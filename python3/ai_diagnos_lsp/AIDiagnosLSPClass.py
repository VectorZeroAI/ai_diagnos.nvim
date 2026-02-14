#!/usr/bin/env python3

from pygls.lsp.server import LanguageServer
import os
import logging
import threading
from pygls.workspace import TextDocument
from lsprotocol import types
import time

from ai_diagnos_lsp.analysers.BasicDiagnoseFunction import BasicDiagnoseFunctionWorker
from ai_diagnos_lsp.DiagnosticsHandlingSubsystem.main import DiagnosticsHandlingSubsystemFactory

class AIDiagnosLSP(LanguageServer):
    """
    My language server class. 
    It is pull diagnostics based. 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}
        self.last_diagnostic_time = {}
        self.config = {}
        self.diagnostics_lock = threading.Lock()
        self.DiagnosticsHandlingSubsystem = DiagnosticsHandlingSubsystemFactory(self)

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.basicConfig(
                    filename="ai_diagnos_lsp.log",
                    level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S'
                    )

    def BasicDiagnose(self, doc: TextDocument):
        """
        The basic diagnose function. It checks if the document should be diagnosed
        if yes it starts a diagnostics thread. 
        If no, it ... says so . 
        """

        max_file_size = self.config["max_file_size"]

        debounce_ms = self.config["debounce_ms"]
        
        if len(doc.lines) > max_file_size:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "File size is too big. Rejecting"))
            return

        if doc.uri not in self.last_diagnostic_time:
            self.last_diagnostic_time[doc.uri] = 0

        if not time.time() - self.last_diagnostic_time[doc.uri] >= debounce_ms / 1000:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "Debounced the diagnostic"))
            return

        threading.Thread(target=BasicDiagnoseFunctionWorker, args=(doc, self)).start()

        self.last_diagnostic_time[doc.uri] = time.time()
