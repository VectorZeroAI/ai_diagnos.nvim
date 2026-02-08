#!/usr/bin/env python3

from typing import List, Union, Tuple
from pydantic import SecretStr
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from lsprotocol import types

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from pathlib import Path

import re

import threading
import logging
import os

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


def init_ai(api_key_input: str):
    global Llm
    global GENERAL_ANALYSIS_SYSTEM_PROMPT
    global GeneralAnalysisPrompt
    global GeneralAnalysisChain
    global DiagnosticsOutputObjekt
    Llm = ChatOpenAI(
            model="tngtech/tng-r1t-chimera:free",
            api_key=SecretStr(api_key_input), 
            base_url="https://openrouter.ai/api/v1"
            )
    try:
        with open(f"{Path(__file__).absolute().resolve().parent}/general_analysis_system_prompt.txt", "r") as f:
            GENERAL_ANALYSIS_SYSTEM_PROMPT = f.read()
    except FileNotFoundError as e:
        raise NotImplementedError("The prompt file is missing. Go write it") from e
    GeneralAnalysisPrompt = ChatPromptTemplate.from_messages([
            ("system", f"{GENERAL_ANALYSIS_SYSTEM_PROMPT}"),
            ("human", "\n{{file_content}}\n\n"),
            ], template_format="mustache")
    class DiagnosticsPydanticObjekt(BaseModel):
        class SingleDiagnostic(BaseModel):

            location: str
            error_message: str
            severity_level: int

            # TODO : Double check if this is enough

            class Config:
                populate_by_name = True

        diagnostics: List[SingleDiagnostic]

    GeneralDiagnosticsOutputParser = PydanticOutputParser(pydantic_object=DiagnosticsPydanticObjekt)

    GeneralAnalysisChain = GeneralAnalysisPrompt | Llm | GeneralDiagnosticsOutputParser

def PingingThread():
    from time import sleep
    global pinging_thread_work
    while pinging_thread_work:
        logging.info("Lanchain is still invoking")
        sleep(1)
    logging.info("Langhchain stopped")

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
            global pinging_thread_work
            pinging_thread_work = True

    def parse(self, document: TextDocument):
        _, previous = self.diagnostics.get(document.uri, (0, []))
        diagnostics = []

        severity_map = {
                1: types.DiagnosticSeverity.Error,
                2: types.DiagnosticSeverity.Warning,
                3: types.DiagnosticSeverity.Information,
                4: types.DiagnosticSeverity.Hint
                }

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("starting the chain")
            threading.Thread(target=PingingThread, daemon=True).start()
            logging.info(f"chain started with input document as {document.source}")

        tmp = GeneralAnalysisChain.invoke({
            "file_content": f"{document.source}"
            })

        global pinging_thread_work
        pinging_thread_work = False

        for i in tmp.diagnostics:
            try:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("searching the file with grep. ")
                    logging.info(f"searching for : {i.location} ; in {document.uri}")
                pos = grep(i.location, document.source)[0]
                pos_line = pos[0]
                pos_char = pos[1]
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info(f"found {i.location} at line : {pos_line}, char : {pos_char}")
            except IndexError:
                # Ignore the diagnostic entirely, because if no matches were found, it means that the AI
                # halucinated, wich makes this one specific diagnostic is wrong, wich is not worth the hassle
                # to try to use. So it is skipped. This is by design, not an error. 

                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("Errored out. Most likely a halucinated citation.")
                continue 
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info(f"DIAGNOSTIC : error message:  {i.error_message} ; severity level : {i.severity_level} ; pos line : {pos_line} ; pos char :  {pos_char}")

            severity_level_converted = severity_map.get(i.severity_level)

            diagnostics.append(
                    types.Diagnostic(
                        message=i.error_message,
                        severity=severity_level_converted,
                        range=types.Range(
                            start=types.Position(pos_line, pos_char),
                            end=types.Position(pos_line, pos_char)
                            ), 
                        source="AI diagnos LSP"
                        )
                    )
        if previous != diagnostics:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("publishing diagnostics I guess....")
            self.diagnostics[document.uri] = (document.version, diagnostics)


def main():
    global config

    server = AI_diagnos_lsp('ai_diagnos', "v0.2 DEV")
    
    @server.feature(types.INITIALIZE)
    def on_startup(ls: AI_diagnos_lsp, params: types.InitializeParams):
        global _flag_callback_ran
        _flag_callback_ran = False

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("INITIALIZE RAN")
            logging.info(f"initialise params = {params}")

        global config

        try:

            params_config = types.ConfigurationParams(
                items=[
                    types.ConfigurationItem(section="api_key")
                    # NOTE : This is a list, of items of type configuration Item, and
                    # Each of those items practically tells the editor what configuration value were looking for
                    # I assume no scope will take the global scope. 
                ]
            )
        except Exception as e:

            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("couldnt form the configuration request's parameters")
            raise RuntimeError("lines 184 - 189 . couldnt form the configuration request's parameters") from e

        def callback(config):

            global _flag_callback_ran
            global api_key
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("callback ran")
            try:
                api_key = config[0]
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error("couldnt asign api_key from config[0], line 206")
                raise RuntimeError("couldnt asign api_key from config[0], line 206") from e
            _flag_callback_ran = True
            
        
        try: 
            config = ls.workspace_configuration(params_config, callback)

        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("couldnt get the workspace configuration. ")

            raise RuntimeError("line 201 , couldnt get the workspace configuration. ") from e

        global api_key

        if not _flag_callback_ran:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("callback didnt run when it was supposed to . ")

            raise RuntimeError("callback didnt run when it was supposed to . ")

        try:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                try:
                    logging.info(f"running init_ai() with api key of the following length: {len(api_key)}")
                except Exception as e:
                    logging.error("couldnt compute the length of api_key.")
                    if api_key is None:
                        logging.error("api key is none")
                        raise RuntimeError("api key is None") from e

            init_ai(api_key)

        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("couldnt run the init_ai function. line 208")

            raise RuntimeError("couldnt run the init_ai function. line 208") from e

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: AI_diagnos_lsp, params: types.DidOpenTextDocumentParams):
        """ Diagnose each document when it is opened """
        doc = ls.workspace.get_text_document(params.text_document.uri)
        ls.parse(doc)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: AI_diagnos_lsp, params: types.DidSaveTextDocumentParams):
        """ Diagnose each document when it is saved, e.g. on save. As was done by the previous version of the plugin """
        doc = ls.workspace.get_text_document(params.text_document.uri)
        ls.parse(doc)

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

    server.start_io()

