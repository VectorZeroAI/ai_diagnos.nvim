#!/usr/bin/env python3

import sqlite3
import threading
from lsprotocol import types
from pygls.lsp.server import LanguageServer
import time

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import DiagnosticsPydanticObjekt

class DiagnosticsHandlingSubsystem:
    """
    My own internal subsyste for handling many different internal types of diagnostics,
    as well as diagnostics saving and reusal. 
    
    Will propably get its own directory once actually implemented. 
    """
    def __init__(self, ls: LanguageServer, sqlite_db_name: str = "diagnostics.db", ttl_seconds: int = 2592000) -> None:
        self.conn = sqlite3.connect(sqlite_db_name)
        self.curr = self.conn.cursor()
        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS files(
            uri TEXT PRIMARY KEY,
            hash TEXT KEY NOT NULL,
            last_changed_at INT NOT NULL
            )
                          """)
        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics(
            uri TEXT PRIMARY KEY,
            diagnostics TEXT NOT NULL,
            created_at INT
            )
                          """)


    def register_new_diagnostics(self, diagnostics: DiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

    def get_saved_diagnostics_for_doc(self, document_uri: str) -> DiagnosticsPydanticObjekt:
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

    def TTLBasedPruningThread(self):
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

