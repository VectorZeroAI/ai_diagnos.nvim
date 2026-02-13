#!/usr/bin/env python3

import sqlite3
import threading
from typing import Tuple
from lsprotocol import types
from pygls.lsp.server import LanguageServer
import time
import logging
import os

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import DiagnosticsPydanticObjekt
from ai_diagnos_lsp.utils.grep import grep
from ai_diagnos_lsp.utils.AIDiagnosLSPClassDummy import AI_Diagnos_LSP_dummy

class DiagnosticsHandlingSubsystemClass:
    """
    My own internal subsyste for handling many different internal types of diagnostics,
    as well as diagnostics saving and reusal. 
    
    Will propably get its own directory once actually implemented. 
    """
    def __init__(self, ls: AI_Diagnos_LSP_dummy | LanguageServer, sqlite_db_name: str = "diagnostics.db", ttl_seconds: int = 2592000) -> None:
        self.conn = sqlite3.connect(sqlite_db_name, autocommit=True)
        self.curr = self.conn.cursor()
        self.ls = ls
        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS files(
            uri TEXT PRIMARY KEY,
            hash TEXT KEY,
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
            INSERT INTO files(last_changed_at) VALUES (?) WHERE uri = ?
                              """, (time.time(), document_uri))


    def register_new_diagnostic(self, diagnostics: DiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        self.curr.execute("""
        INSERT INTO diagnostics(uri, diagnostics, created_at) VALUES(?, ?, ?)
                          """, (document_uri, diagnostics.model_dump_json(), time.time()))


    def publish_diagnostics_for_file(self, document_uri: str) -> bool:
        """
        This function DIRECTLY PUBLISHES the diagnostics for a file. 
        """
        diagnostics_converted_list = []

        json_diagnostics_list = self.curr.execute("""
        SELECT diagnostics FROM diagnostics WHERE uri = ?
                          """, (document_uri)).fetchall()
        
        pydantic_objekts_list = []
        for i in json_diagnostics_list:
            pydantic_objekts_list.append(
                    DiagnosticsPydanticObjekt.model_validate_json(i)
                    )


        severity_map = {
                1: types.DiagnosticSeverity.Error,
                2: types.DiagnosticSeverity.Warning,
                3: types.DiagnosticSeverity.Information,
                4: types.DiagnosticSeverity.Hint
                }

        document = self.ls.workspace.get_text_document(document_uri)

        for i in pydantic_objekts_list:
            for j in i.diagnostics:

                try:
                    if os.getenv("AI_DIAGNOS_LOG") is not None:
                        logging.info("searching the file with grep. ")
                        logging.info(f"searching for : {i.location} ; in {document.uri}")
                    
                    if isinstance(j.location, Tuple):
                        pos = grep(j.location[0], document.source)[j.location[1] - 1]
                    else:
                        pos = grep(j.location, document.source)[0]
                    pos_line = pos[0]
                    pos_char = pos[1]
                    if os.getenv("AI_DIAGNOS_LOG") is not None:
                        logging.info(f"found {j.location} at line : {pos_line}, char : {pos_char}")
                except IndexError as e:
                    # Ignore the diagnostic entirely, because if no matches were found, it means that the AI
                    # halucinated, wich makes this one specific diagnostic is wrong, wich is not worth the hassle
                    # to try to use. So it is skipped. This is by design, not an error. 

                    if os.getenv("AI_DIAGNOS_LOG") is not None:
                        logging.info(f"Errored out. Most likely a halucinated citation. The error : {e}")
                    continue 

                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info(f"DIAGNOSTIC : error message:  {j.error_message} ; severity level : {j.severity_level} ; pos line : {pos_line} ; pos char :  {pos_char}")

                severity_level_converted = severity_map.get(j.severity_level)

                diagnostics_converted_list.append(
                        types.Diagnostic(
                            message=j.error_message,
                            severity=severity_level_converted,
                            range=types.Range(
                                start=types.Position(pos_line, pos_char),
                                end=types.Position(pos_line, pos_char)
                                ), 
                            source="AI diagnos LSP", data="AI",code="AI",
                            code_description=types.CodeDescription(" This is AI generated Diagnostics. I am putting this wherever I can because why not ?  ")
                            )
                        )
        with self.ls.diagnostics_lock:
            self.ls.diagnostics[document_uri] = (document.version, diagnostics_converted_list)

    




    def TTLBasedPruningThread(self):
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

def DiagnosticsHandlingSubsystemFactory(ls: LanguageServer,
                                        sqlite_db_name: str = "diagnostics.db",
                                        ttl_seconds: int = 2592000
                                        ) -> DiagnosticsHandlingSubsystemClass:
    return DiagnosticsHandlingSubsystemClass(ls=ls, 
                                             sqlite_db_name=sqlite_db_name,
                                             ttl_seconds=ttl_seconds
                                             )
