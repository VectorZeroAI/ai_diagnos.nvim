#!/usr/bin/env python3

from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING
import logging
import os
from pygls.workspace import TextDocument
from lsprotocol import types

if TYPE_CHECKING:
    from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsPydanticObjekt
from ai_diagnos_lsp.utils.grep import grep

severity_map = {
        1: types.DiagnosticSeverity.Error,
        2: types.DiagnosticSeverity.Warning,
        3: types.DiagnosticSeverity.Information,
        4: types.DiagnosticSeverity.Hint
        }


def GeneralDiagnosticsPydanticToLSProtocol(ls: AIDiagnosLSP,
                                           pydantic_objekts_list: List[GeneralDiagnosticsPydanticObjekt],
                                           document: TextDocument | str
                                           ) -> List[types.Diagnostic]:
    """

    """
    diagnostics_converted_list = []

    for i in pydantic_objekts_list:
        for j in i.diagnostics:

            try:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("searching the file with grep.")
                    if isinstance(document, TextDocument):
                        logging.info(f"searching for : {j.location} ; in {document.uri}")
                    else:
                        logging.info(f"searching for : {j.location} ; in {document}")
                
                if isinstance(j.location, Tuple):
                    if isinstance(document, TextDocument):
                        pos = grep(j.location[0], document.source)[j.location[1] - 1]
                    else:
                        pos = grep(j.location[0], document)[j.location[1] - 1]
                else:
                    if isinstance(document, TextDocument):
                        pos = grep(j.location, document.source)[0]
                    else:
                        pos = grep(j.location, document)[0]
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
                        code_description=types.CodeDescription("This is AI generated Diagnostics. I am putting this wherever I can because why not ?")
                        )
                    )
    return diagnostics_converted_list
