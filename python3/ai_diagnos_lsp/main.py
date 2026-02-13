#!/usr/bin/env python3

from typing import Sequence, Any

from lsprotocol import types

from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

def main():
    """
    The server setup function. 
    """
    server = AIDiagnosLSP('ai_diagnos', "v0.8.4 DEV")
    
    @server.feature(types.INITIALIZE)
    def on_startup(ls: AIDiagnosLSP, params: types.InitializeParams):
        """
        The configuration getting and saving function. 
        pretty much sets the ls.config map
        """

        assert params.initialization_options is not None
        for i in params.initialization_options:
            ls.config[i] = params.initialization_options.get(i)

    @server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
    def on_did_change(ls: AIDiagnosLSP, params: types.DidChangeTextDocumentParams):
        """ Publish diagnostics from DB to the client on change. e.g. refresh them. """
        ls.DiagnosticsHandlingSubsystem.load_diagnostics_for_file(params.text_document.uri)

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: AIDiagnosLSP, params: types.DidOpenTextDocumentParams):
        """ Try co load saved diagnostics forthe file, if fails, analyse.  """
        doc = ls.workspace.get_text_document(params.text_document.uri)

        if not ls.DiagnosticsHandlingSubsystem.load_diagnostics_for_file(doc.uri):
            ls.BasicDiagnose(doc)
            ls.DiagnosticsHandlingSubsystem.load_diagnostics_for_file(doc.uri)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: AIDiagnosLSP, params: types.DidSaveTextDocumentParams):
        """ Diagnose each document when it is saved, e.g. on save. As was done by the previous version of the plugin """
        doc = ls.workspace.get_text_document(params.text_document.uri)
        ls.DiagnosticsHandlingSubsystem.register_file_write(doc.uri)
        ls.BasicDiagnose(doc)
        ls.DiagnosticsHandlingSubsystem.load_diagnostics_for_file(doc.uri)

    @server.feature(
            types.TEXT_DOCUMENT_DIAGNOSTIC,
            types.DiagnosticOptions(
                identifier="pull-diagnostics",
                inter_file_dependencies=False,
                workspace_diagnostics=True,
                ),
            )
    def document_diagnostic(ls: AIDiagnosLSP, params: types.DocumentDiagnosticParams):
        """ Return diagnostics for the requested document """
        
        if (uri := params.text_document.uri) not in ls.diagnostics:
            return

        version, diagnostics = ls.diagnostics[uri]
        result_id = f"{uri}@{version}"

        if result_id == params.previous_result_id:
            return types.UnchangedDocumentDiagnosticReport(result_id)

        return types.FullDocumentDiagnosticReport(items=diagnostics, result_id=result_id)

    @server.feature(types.WORKSPACE_DIAGNOSTIC)
    def workspace_diagnostic( ls: AIDiagnosLSP, params: types.WorkspaceDiagnosticParams ):
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
    def AnalyseDocument(ls: AIDiagnosLSP, params: Sequence[ Any | None ]):
        """ Analyses a document by URI . REQUIRES a URI as its parameter """
        try:
            assert params[0] is not None
            doc = ls.workspace.get_text_document(params[0])
        except Exception as e:
            ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Couldnt get the URI parameter due to the following error {e}"))
            return
        else:
            ls.BasicDiagnose(doc)
            # TODO : Add good logging
    
    @server.command("Clear.AIDiagnostics")
    def ClearAIDiagnostics(ls: AIDiagnosLSP, params: Sequence[Any | None]):
        """ Clears AI diagnostics for the provided URI """
        ls.diagnostics[params[0]] = (None, None)
        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), "successfully cleared the diagnostics"))

    @server.command("Clear.AIDiagnostics.All")
    def ClearAllAIDiagnostics(ls: AIDiagnosLSP, params: Sequence[Any | None]):
        """ Clears ALL the AI diagnostics """
        for i in ls.diagnostics:
            ls.diagnostics[i] = (None, None)
        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), "succesfully cleared the diagnostics"))

    server.start_io()

