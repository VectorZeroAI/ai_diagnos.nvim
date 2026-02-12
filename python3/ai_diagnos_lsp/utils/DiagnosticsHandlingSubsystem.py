#!/usr/bin/env python3

import sqlite3
import threading
from lsprotocol import types

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import DiagnosticsPydanticObjekt

class DiagnosticsHandlingSubsystem:
    def __init__(self, sqlite_db_name: str = "diagnostics.db", ttl_seconds: int = 2592000) -> None:
        self.conn = sqlite3.connect(sqlite_db_name)
        self.curr = self.conn.cursor()
        self.curr.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics(
        uri PRIMARY KEY STRING,
        hash 

            )
                          """)

    def register_new_diagnostics(self, diagnostics: DiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

    def get_saved_diagnostics_for_doc(self, document_uri: str) -> DiagnosticsPydanticObjekt:
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

    def TTLBasedPruningThread(self):
        raise NotImplementedError("Custom Diagnostics handling subsystem not yet implemented")

