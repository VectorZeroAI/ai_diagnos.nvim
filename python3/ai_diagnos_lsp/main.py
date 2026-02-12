#!/usr/bin/env python3

import threading
from typing import Sequence, Any
from pygls.lsp.server import LanguageServer

from lsprotocol import types

import os

import logging

from pygls.workspace import TextDocument

import time

from ai_diagnos_lsp.analysers.BasicDiagnoseFunction import BasicDiagnoseFunctionWorker

class AI_diagnos_lsp(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}
        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.basicConfig(
                    filename="ai_diagnos_lsp.log",
                    level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S'
                    )
        self.last_diagnostic_time = {}
        self.config = {}
        self.diagnostics_lock = threading.Lock()

    def BasicDiagnose(self, doc: TextDocument):

        max_file_size = self.config["max_file_size"]

        debounce_ms = self.config["debounce_ms"]
        
        if len(doc.lines) > max_file_size:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "File size is to big. Rejecting"))
            return

        if doc.uri not in self.last_diagnostic_time:
            self.last_diagnostic_time[doc.uri] = 0

        if not time.time() - self.last_diagnostic_time[doc.uri] >= debounce_ms / 1000:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "Debounced the diagnostic"))
            return

        threading.Thread(target=BasicDiagnoseFunctionWorker, args=(doc, self)).start()

        self.last_diagnostic_time[doc.uri] = time.time()

def main():
    server = AI_diagnos_lsp('ai_diagnos', "v0.7 DEV")
    
    @server.feature(types.INITIALIZE)
    def on_startup(ls: AI_diagnos_lsp, params: types.InitializeParams):

        assert params.initialization_options is not None
        for i in params.initialization_options:
            ls.config[i] = params.initialization_options.get(i)


    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: AI_diagnos_lsp, params: types.DidOpenTextDocumentParams):
        """ Diagnose each document when it is opened """
        doc = ls.workspace.get_text_document(params.text_document.uri)
        ls.BasicDiagnose(doc)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: AI_diagnos_lsp, params: types.DidSaveTextDocumentParams):
        """ Diagnose each document when it is saved, e.g. on save. As was done by the previous version of the plugin """
        doc = ls.workspace.get_text_document(params.text_document.uri)
        ls.BasicDiagnose(doc)

    @server.feature(
            types.TEXT_DOCUMENT_DIAGNOSTIC,
            types.DiagnosticOptions(
                identifier="pull-diagnostics",
                inter_file_dependencies=False,
                workspace_diagnostics=True,
                ),
            )
    def document_diagnostic(ls: AI_diagnos_lsp, params: types.DocumentDiagnosticParams):
        """ Return diagnostics for the requested document """
        
        if (uri := params.text_document.uri) not in ls.diagnostics:
            return

        version, diagnostics = ls.diagnostics[uri]
        result_id = f"{uri}@{version}"

        if result_id == params.previous_result_id:
            return types.UnchangedDocumentDiagnosticReport(result_id)

        return types.FullDocumentDiagnosticReport(items=diagnostics, result_id=result_id)

    @server.feature(types.WORKSPACE_DIAGNOSTIC)
    def workspace_diagnostic( ls: AI_diagnos_lsp, params: types.WorkspaceDiagnosticParams ):
        """Return diagnostics for the workspace."""
        # logging.info("%s", params)
        items = []
        previous_ids = {result.value for result in params.previous_result_ids}

        for uri, (version, diagnostics) in ls.diagnostics.items():
            result_id = f"{uri}@{version}"
            if result_id in previous_ids:
                items.append(
                    types.WorkspaceUnchangedDocumentDiagnosticReport(
                        uri=uri, result_id=result_id, version=version
                    )
                )
            else:
                items.append(
                    types.WorkspaceFullDocumentDiagnosticReport(
                        uri=uri,
                        version=version,
                        items=diagnostics,
                    )
                )

        return types.WorkspaceDiagnosticReport(items=items)

    @server.command("Analyse.Document")
    def AnalyseDocument(ls: AI_diagnos_lsp, params: Sequence[ Any | None ]):
        """ Analyses a document by URI . REQUIRES a URI as its parameter """
        try:
            assert params[0] is not None
            doc = ls.workspace.get_text_document(params[0])
        except Exception:
            ls.window_show_message(types.ShowMessageParams(types.MessageType(1), "Couldnt get the URI parameter due to the following error {e}"))
            return
        else:
            ls.BasicDiagnose(doc)
            # TODO : Add good logging
    
    @server.command("Clear.AIDiagnostics")
    def ClearAIDiagnostics(ls: AI_diagnos_lsp, params: Sequence[Any | None]):
        """ Clears AI diagnostics for the provided URI """
        ls.diagnostics[params[0]] = {}
        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), "succesfully cleared the diagnostics"))

    @server.command("Clear.AIDiagnostics.All")
    def ClearAllAIDiagnostics(ls: AI_diagnos_lsp, params: Sequence[Any | None]):
        """ Clears ALL the AI diagnostics """
        for i in ls.diagnostics:
            ls.diagnostics[i] = {}
        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), "succesfully cleared the diagnostics"))

    server.start_io()

