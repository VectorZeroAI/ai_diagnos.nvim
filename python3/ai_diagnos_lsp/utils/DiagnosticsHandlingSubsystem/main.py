#!/usr/bin/env python3

from __future__ import annotations
import sqlite3
from typing import TYPE_CHECKING
import time
import logging
import os

from lsprotocol import types

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsPydanticObjekt

if TYPE_CHECKING:
    from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

from ai_diagnos_lsp.utils.DiagnosticsHandlingSubsystem.Converters.GeneralDiagnosticsPydanticToLSProtocol import GeneralDiagnosticsPydanticToLSProtocol

class DiagnosticsHandlingSubsystemClass:
    """
    My own internal subsyste for handling many different internal types of diagnostics,
    as well as diagnostics saving and reusal. 
    
    Will propably get its own directory once actually implemented. 
    """
    def __init__(self, ls: AIDiagnosLSP, sqlite_db_name: str = "diagnostics.db", ttl_seconds: int = 2592000) -> None:
        self.ls = ls
        self.ttl_seconds = ttl_seconds

        self.conn = sqlite3.connect(sqlite_db_name, autocommit=True, check_same_thread=False)
        self.curr = self.conn.cursor()
        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS files(
            uri TEXT PRIMARY KEY,
            hash TEXT UNIQUE,
            last_changed_at REAL NOT NULL
            )
                          """)

        # TODO: Add hashe based renaming detection. 

        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics(
            uri TEXT UNIQUE,
            diagnostics TEXT UNIQUE,
            created_at REAL NOT NULL
            )
                          """)

    def register_file_write(self, document_uri: str):
        tmp = self.curr.execute("""
        SELECT uri FROM files WHERE uri = ?
                                """, (document_uri,)).fetchall()

        if len(tmp) > 0:
            self.curr.execute("""
            UPDATE files SET last_changed_at = ? WHERE uri = ?
                              """, (time.time(), document_uri))
        else:
            self.curr.execute("""
            INSERT INTO files(last_changed_at, uri) VALUES (?, ?)
                              """, (time.time(), document_uri))


    def register_new_diagnostic(self, diagnostics: GeneralDiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        """
        Registers the diagnostic to the DataBase. DOES NOT PUBLISH THEM TO THE CLIENT
        """
        try:
            self.curr.execute("""
            INSERT INTO diagnostics(uri, diagnostics, created_at) VALUES(?, ?, ?)
                              """, (document_uri, diagnostics.model_dump_json(), time.time()))
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt register new diagnosic due to following error: {e}")
            return False
        else:
            self.ls.workspace_diagnostic_refresh(None).result()
            return True


    def publish_diagnostics_for_file(self, document_uri: str) -> bool:
        """
        This function DIRECTLY PUBLISHES the diagnostics for a file. 
        MUST BE CALLED AFTER register_new_diagnostic.
        """
        try:
            json_diagnostics_list = self.curr.execute("""
            SELECT diagnostics FROM diagnostics WHERE uri = ?
                              """, (document_uri,)).fetchall()
            
            pydantic_objekts_list = []
            for i in json_diagnostics_list:
                pydantic_objekts_list.append(
                        GeneralDiagnosticsPydanticObjekt.model_validate_json(i[0])
                        )
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt load diagnostics due to following error : {e}")
            return False

        document = self.ls.workspace.get_text_document(document_uri)

        diagnostics_lsprotocol_final_list = []

        try:
            diagnostics_lsprotocol_list = GeneralDiagnosticsPydanticToLSProtocol(self.ls, pydantic_objekts_list, document)
            for i in diagnostics_lsprotocol_list:
                diagnostics_lsprotocol_final_list.append(i)
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"couldnt convert diagnostics from pydantic to lsprotocol standarts due to the following error : {e}")
            return False

        try:
            with self.ls.diagnostics_lock:
                self.ls.diagnostics[document_uri] = (document.version, diagnostics_lsprotocol_final_list)
            self.ls.workspace_diagnostic_refresh(None).result()
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt publish diagnostics due to the following reason: {e}")
            self.ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Couldnt publish diagnostics for the following reason : {e}"))
            return False

        return True
        
    
    def TTLBasedPruningThread(self):
        raise NotImplementedError()

def DiagnosticsHandlingSubsystemFactory(ls: AIDiagnosLSP,
                                        sqlite_db_name: str = "diagnostics.db",
                                        ttl_seconds: int = 2592000
                                        ) -> DiagnosticsHandlingSubsystemClass:
    return DiagnosticsHandlingSubsystemClass(ls=ls, 
                                             sqlite_db_name=sqlite_db_name,
                                             ttl_seconds=ttl_seconds
                                             )
