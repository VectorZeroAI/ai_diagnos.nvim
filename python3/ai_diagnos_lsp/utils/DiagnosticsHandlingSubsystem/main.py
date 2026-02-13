#!/usr/bin/env python3

from __future__ import annotations
import sqlite3
import threading
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
    def __init__(self,
                 ls: AIDiagnosLSP,
                 sqlite_db_name,
                 ttl_seconds_until_deletion,
                 ttl_seconds_until_invalidation
                 ) -> None:
        self.ls = ls
        self.ttl_seconds_until_deletion = ttl_seconds_until_deletion
        self.db_lock = threading.Lock()
        self.ttl_seconds_until_invalidation = ttl_seconds_until_invalidation

        threading.Thread(target=self.TTLBasedDeletionThread, daemon=True, args=(self,)).start()
        threading.Thread(target=self.TTLBasedDiagnosticsInvalidationThread, daemon=True, args=(self,)).start()
        
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
            uri TEXT NOT NULL,
            diagnostics TEXT UNIQUE,
            created_at REAL NOT NULL
            )
                          """)

    def register_file_write(self, document_uri: str):
        try:
            with self.db_lock:
                tmp = self.curr.execute("""
                SELECT uri FROM files WHERE uri = ?
                                        """, (document_uri,)).fetchall()

            if len(tmp) > 0:
                with self.db_lock:
                    self.curr.execute("""
                    UPDATE files SET last_changed_at = ? WHERE uri = ?
                                      """, (time.time(), document_uri))
            else:
                with self.db_lock:
                    self.curr.execute("""
                    INSERT INTO files(last_changed_at, uri) VALUES (?, ?)
                                      """, (time.time(), document_uri))
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"register file write encoutered the following error: {e}")
            raise Exception(f"register file write encoutered the following exeption: {e}") from e


    def save_new_diagnostic(self, diagnostics: GeneralDiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        """
        Registers the diagnostic to the DataBase. DOES NOT PUBLISH THEM TO THE CLIENT
        """
        try:
            with self.db_lock:
                self.curr.execute("""
                INSERT INTO diagnostics(uri, diagnostics, created_at) VALUES(?, ?, ?)
                                  """, (document_uri, diagnostics.model_dump_json(), time.time()))
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt register new diagnosic due to following error: {e}")
            return False
        else:
            self.ls.workspace_diagnostic_refresh(None)
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("sucsessfully registered new diagnostics")
            return True


    def load_diagnostics_for_file(self, document_uri: str) -> bool:
        """
        This function DIRECTLY PUBLISHES the diagnostics for a file. 
        MUST BE CALLED AFTER register_new_diagnostic.
        """
        try:
            with self.db_lock:
                json_diagnostics_list = self.curr.execute("""
                SELECT diagnostics FROM diagnostics WHERE uri = ?
                                  """, (document_uri,)).fetchall()

            if not len(json_diagnostics_list):
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.warning(f"No diagnostics for the file found . File : {document_uri}")
                return False
            
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
            self.ls.workspace_diagnostic_refresh(None)
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt publish diagnostics due to the following reason: {e}")
            self.ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Couldnt publish diagnostics for the following reason : {e}"))
            return False

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("Sucsessfully published diagnostics. ")
        return True
        
    
    def TTLBasedDeletionThread(self):
        while True:
            try:
                with self.db_lock:
                    last_writes_list = self.curr.execute("""
                    SELECT last_changed_at, uri FROM files
                                      """).fetchall()
                for i in last_writes_list:
                    if time.time() - i[0] > self.ttl_seconds_until_deletion:
                        if os.getenv("AI_DIAGNOS_LOG") is not None:
                            logging.info("file: {i[1]}, last_changed_at: {i[0]}")
                        with self.db_lock:
                            self.curr.execute("""
                            DELETE FROM files WHERE uri = ?
                                              """, (i[1],))
                            self.curr.execute("""
                            DELETE FROM diagnostics WHERE uri = ?
                                              """, (i[1],))
                time.sleep(60)
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error(f"TTLBasedDeletionThread encoutered the following problem : {e}")

    def TTLBasedDiagnosticsInvalidationThread(self):
        """
    This thread checks for every diagnostic present its corresponding files last_change time, e.g. last
    write to it time, then
    matches it against the diagnostics creation time (via -), 
    and if the result is smaller then self.ttl_seconds_until_invalidation, 
    the diagnostic gets deleted from the DB. 
        """
        while True:
            try:
                with self.db_lock:
                    all_diagnostics = self.curr.execute("""
                    SELECT uri, created_at, diagnostics FROM diagnostics
                                                  """).fetchall()

                for i in all_diagnostics:
                    with self.db_lock:
                        file_change_time = self.curr.execute("""
                        SELECT last_changed_at FROM files WHERE uri = ?
                                                 """, (i[0],)).fetchone()

                    if i[1] - file_change_time[0] < self.ttl_seconds_until_invalidation:
                    # This line means : 
                    # if diagnostic_creation_timestamp - last change time, in unix epoch
                    # Wich is a negative float, IS SMALLER THEN a positive integer self.ttl seconds until invalidation
                    # Then invalidate (delete) that diagnostics entry. 
                        with self.db_lock:
                            self.curr.execute("""
                            DELETE FROM diagnostics WHERE diagnostics = ?
                                              """, (i[2],))
                        
                time.sleep(2)
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error(f"TTLBasedDiagnosticsInvalidationThread encoutered the follwoign error: {e}")

def DiagnosticsHandlingSubsystemFactory(ls: AIDiagnosLSP,
                                        sqlite_db_name: str = "diagnostics.db",
                                        ttl_seconds_until_deletion: int = 2592000,
                                        ttl_seconds_until_invalidation: int = 15
                                        ) -> DiagnosticsHandlingSubsystemClass:
    return DiagnosticsHandlingSubsystemClass(ls=ls, 
                                             sqlite_db_name=sqlite_db_name,
                                             ttl_seconds_until_deletion=ttl_seconds_until_deletion,
                                             ttl_seconds_until_invalidation= ttl_seconds_until_invalidation
                                             )
