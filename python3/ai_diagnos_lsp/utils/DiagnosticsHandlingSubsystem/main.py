#!/usr/bin/env python3

from __future__ import annotations
import sqlite3
import threading
from typing import Tuple, TYPE_CHECKING
from lsprotocol import types
import time
import logging
import os

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsPydanticObjekt
from ai_diagnos_lsp.utils.grep import grep

if TYPE_CHECKING:
    from ai_diagnos_lsp.main import AI_diagnos_lsp

from ai_diagnos_lsp.utils.DiagnosticsHandlingSubsystem.Converters.GeneralDiagnosticsPydanticToLSProtocol import GeneralDiagnosticsPydanticToLSProtocol

class DiagnosticsHandlingSubsystemClass:
    """
    My own internal subsyste for handling many different internal types of diagnostics,
    as well as diagnostics saving and reusal. 
    
    Will propably get its own directory once actually implemented. 
    """
    def __init__(self, ls: AI_Diagnos_lsp, sqlite_db_name: str = "diagnostics.db", ttl_seconds: int = 2592000) -> None:
        self.conn = sqlite3.connect(sqlite_db_name, autocommit=True)
        self.curr = self.conn.cursor()
        self.ls = ls
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
            uri TEXT NOT NULL,
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
        self.curr.execute("""
        INSERT INTO diagnostics(uri, diagnostics, created_at) VALUES(?, ?, ?)
                          """, (document_uri, diagnostics.model_dump_json(), time.time()))


    def publish_diagnostics_for_file(self, document_uri: str) -> bool:
        """
        This function DIRECTLY PUBLISHES the diagnostics for a file. 
        """
        try:
            json_diagnostics_list = self.curr.execute("""
            SELECT diagnostics FROM diagnostics WHERE uri = ?
                              """, (document_uri)).fetchall()
            
            pydantic_objekts_list = []
            for i in json_diagnostics_list:
                pydantic_objekts_list.append(
                        GeneralDiagnosticsPydanticObjekt.model_validate_json(i)
                        )
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("Couldnt load diagnostics")
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
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt publish diagnostics due to the following reason: {e}")
            return False
        
    
    def TTLBasedPruningThread(self):
        raise NotImplementedError()

def DiagnosticsHandlingSubsystemFactory(ls: AI_diagnos_lsp,
                                        sqlite_db_name: str = "diagnostics.db",
                                        ttl_seconds: int = 2592000
                                        ) -> DiagnosticsHandlingSubsystemClass:
    return DiagnosticsHandlingSubsystemClass(ls=ls, 
                                             sqlite_db_name=sqlite_db_name,
                                             ttl_seconds=ttl_seconds
                                             )
