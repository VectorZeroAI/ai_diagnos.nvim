#!/usr/bin/env python3

import threading
from typing import List, Sequence, Union, Tuple, Any
from pygls.lsp.server import LanguageServer

from lsprotocol import types

import re
import os

import logging

from pygls.workspace import TextDocument

import time


def grep(pattern: str, lines: Union[str, List[str]], ignore_case: bool = False) -> List[Tuple[int, int]]:
    """
    Search for a pattern and return (line_number, character_position) for each match.
    
    Args:
        pattern: The pattern to search for
        lines: List of strings or a multi-line string
        ignore_case: Case-insensitive matching
    
    Returns:
        List of (line_number, character_position) tuples
    """
    # Convert string to list if needed
    if isinstance(lines, str):
        lines = lines.splitlines()
    
    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)
    
    matches = []
    
    for line_num, line in enumerate(lines, start=0):
        for match in regex.finditer(line):
            matches.append((line_num, match.start()))
    
    return matches

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
        self.last_diagnostic_time = 0
        self.config = {}

    def BasicDiagnose(self, doc: TextDocument):

        max_file_size = os.getenv('max_file_size')
        assert max_file_size is not None
        max_file_size = int(max_file_size)

        debounce_ms = os.getenv('debounce_ms')
        assert debounce_ms is not None
        debounce_ms = int(debounce_ms)
        

        if len(doc.lines) > max_file_size:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "File size is to big. Rejecting"))
            return

        if not time.time() - self.last_diagnostic_time >= debounce_ms / 1000:
            self.window_show_message(types.ShowMessageParams(types.MessageType(2), "Debounced the diagnostic"))
            return

        from ai_diagnos_lsp.analysers.BasicDiagnoseFunction import BasicDiagnoseFunctionWorker

        threading.Thread(target=BasicDiagnoseFunctionWorker, args=(doc, self)).start()

def main():
    server = AI_diagnos_lsp('ai_diagnos', "v0.6 DEV")
    
    @server.feature(types.INITIALIZE)
    def on_startup(ls: AI_diagnos_lsp, params: types.InitializeParams):

        assert params.initialization_options is not None

        assert params.initialization_options["model"] is not None
        assert params.initialization_options["api_key"] is not None
        assert params.initialization_options["timeout_ms"] is not None
        assert params.initialization_options["show_progress"] is not None
        assert params.initialization_options["show_progress_every_ms"] is not None
        assert params.initialization_options["debounce_ms"] is not None
        assert params.initialization_options["max_file_size"] is not None

        os.environ['model_openrouter'] = str(params.initialization_options["model"])
        os.environ['api_key_openrouter'] = str(params.initialization_options["api_key"])
        os.environ['timeout_ms'] = str(params.initialization_options["timeout_ms"])
        os.environ['show_progress'] = str(params.initialization_options["show_progress"])
        os.environ['show_progress_every_ms'] = str(params.initialization_options["show_progress_every_ms"])
        os.environ['debounce_ms'] = str(params.initialization_options["debounce_ms"])
        os.environ['max_file_size'] = str(params.initialization_options["max_file_size"])

        ls.config = {
                "model_openrouter" : str(params.initialization_options["model"]), 
                "api_key_openrouter": str(params.initialization_options["api_key"]),
                "timeout_ms" :  str(params.initialization_options["timeout_ms"]),
                "show_progress" :  str(params.initialization_options["show_progress"]),
                "show_progress_every_ms" :  str(params.initialization_options["show_progress_every_ms"]),
                "debounce_ms" :  str(params.initialization_options["debounce_ms"]),
                "max_file_size" :  str(params.initialization_options["max_file_size"]),
                }


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
    def ClearAIDiagnostics(ls: AI_diagnos_lsp):
        ls.diagnostics = {}
        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), "succesfully cleared the diagnostics"))

    server.start_io()

