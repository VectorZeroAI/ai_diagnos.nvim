#!/usr/bin/env python3

from enum import IntEnum
from typing import List, Union, Tuple
from pydantic import SecretStr
from pygls.cli import start_server
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from lsprotocol import types

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from pathlib import Path

import re

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


def init_ai():
    global Llm
    global GENERAL_ANALYSIS_SYSTEM_PROMPT
    global GeneralAnalysisPrompt
    global GeneralAnalysisChain
    global DiagnosticsOutputObjekt
    Llm = ChatOpenAI(
            model="openrouter/pony-alpha",
            api_key=SecretStr(""), 
            base_url="https://openrouter.ai/api/v1"
            )
    try:
        with open(f"{Path(__file__).absolute().resolve().parent}/general_analysis_system_prompt.txt", "r") as f:
            GENERAL_ANALYSIS_SYSTEM_PROMPT = f.read()
    except FileNotFoundError as e:
        raise NotImplementedError("The prompt file is missing. Go write it") from e    # FIXME : Write the prompt file
    GeneralAnalysisPrompt = ChatPromptTemplate.from_messages([
            ("system", f"{GENERAL_ANALYSIS_SYSTEM_PROMPT}"),
            ("human", "\n{file_content}\n\n"),
            ])
    class DiagnosticsPydanticObjekt(BaseModel):
        class SingleDiagnostic(BaseModel):
            class Severity(IntEnum):
                """ Error Severity Level """
                ERROR = 1
                WARNING = 2
                INFORMATION = 3
                HINT = 4

            class Location(BaseModel):
                """
                Wrong spot citation based location of the error. 
                So you basically citate the wrong place, and we find it
                """
                citation: str
                # TODO : implement the citation to line and colum transformation
                

            range: Location
            message: str
            severity: Severity
            # TODO : Double check if this is enough
            class Config:
                populate_by_name = True

        diagnostics: List[SingleDiagnostic]

    GeneralDiagnosticsOutputParser = PydanticOutputParser(pydantic_object=DiagnosticsPydanticObjekt)

    GeneralAnalysisChain = GeneralAnalysisPrompt | Llm | GeneralDiagnosticsOutputParser

class AI_diagnos_lsp(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}
        init_ai()

    def parse(self, document: TextDocument):
        _, previous = self.diagnostics.get(document.uri, (0, []))
        diagnostics = []
        tmp = GeneralAnalysisChain.invoke({
            "file_content": f"{document.source}"
            })
        for i in tmp.diagnostics:
            try:
                pos = grep(i.location.citation, document.source)[0] # NOTE : EVERYTHING IS SO FUCKED ! 
                pos_line = pos[0]
                pos_char = pos[1]
            except IndexError:
                # Ignore the diagnostic entirely, because if no matches were found, it means that the AI
                # halucinated, wich makes this one specific diagnostic is wrong, wich is not worth the hassle
                # to try to use. So it is skipped. This is by design, not an error. 
                continue 
            diagnostics.append(
                    types.Diagnostic(
                        message=i.message,
                        severity=i.severity,
                        range=types.Range(
                            start=types.Position(pos_line, pos_char),
                            end=types.Position(pos_line, pos_char)
                            ), 
                        source="AI diagnos LSP"
                        )
                    )
        if previous != diagnostics:
            self.diagnostics[document.uri] = (document.version, diagnostics)


server = AI_diagnos_lsp('ai_diagnos', "v0.1")

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: AI_diagnos_lsp, params: types.DidOpenTextDocumentParams):
    """ Parse each document when it is opened """
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


if __name__ == "__main__":
    start_server(server)
