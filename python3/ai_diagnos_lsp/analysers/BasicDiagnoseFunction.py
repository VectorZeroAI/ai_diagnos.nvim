from concurrent.futures import Future
import time
from typing import Any, List, Union, Tuple
from lsprotocol import types
from pygls.workspace import TextDocument
import logging
import os
import asyncio
import threading

from ai_diagnos_lsp.analysers.chains.BasicChainOpenrouter import BasicChainOpenrouter

import re

def BasicDiagnoseFunction(document: TextDocument, ls):
    diagnostics_result: Future[List[Any]] = Future()
    diagnostics = []

    severity_map = {
            1: types.DiagnosticSeverity.Error,
            2: types.DiagnosticSeverity.Warning,
            3: types.DiagnosticSeverity.Information,
            4: types.DiagnosticSeverity.Hint
            }
    if os.getenv("AI_DIAGNOS_LOG") is not None:
        logging.basicConfig(
                filename="ai_diagnos_lsp.log",
                level=logging.DEBUG,
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
                )
    
    debounce_ms_as_string = os.getenv('debounce_ms')
    assert debounce_ms_as_string is not None
    debounce_ms = int(debounce_ms_as_string)

    if os.getenv("AI_DIAGNOS_LOG") is not None:
        logging.info(f"debounce ms recieved = {debounce_ms}")
    
    show_progress_every_ms_as_string = os.getenv('show_progress_every_ms')
    assert show_progress_every_ms_as_string is not None
    show_progress_every_ms = int(show_progress_every_ms_as_string)

    if os.getenv("AI_DIAGNOS_LOG") is not None:
        logging.info(f"debounce ms recieved = {show_progress_every_ms}")

    show_progress_as_string = os.getenv('show_progress')
    assert show_progress_as_string is not None
    show_progress = bool(show_progress_as_string)

    if os.getenv("AI_DIAGNOS_LOG") is not None:
        logging.info(f"debounce ms recieved = {show_progress}")

    max_file_size_as_string = os.getenv('max_file_size')
    assert max_file_size_as_string is not None
    max_file_size = int(max_file_size_as_string)


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

    def BasicDiagnoseFunctionWorker(ls = ls):

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f"debounce ms recieved = {max_file_size}")

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("starting the chain")
            logging.info(f"chain started with input document as {document.source}")

        LangchainTimedOut = False

        async def GeneralAnalysisChainInvokation():
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("Started The async GeneralAnalysisChainInvokation function")
            
            loop = asyncio.get_event_loop()
            
            # Run the blocking invoke() in a thread
            future = loop.run_in_executor(
                None, 
                BasicChainOpenrouter.invoke,
                {"file_content": f"{document.source}"}
            )
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("invoked the langhchain")
            
            counter = 0
            # Poll until done or timeout
            while not LangchainTimedOut:
                if future.done():
                    return future.result()
                await asyncio.sleep(show_progress_every_ms / 1000)  # Check every n seconds
                if show_progress:
                    ls.window_show_message(types.ShowMessageParams(types.MessageType(3), f"Langchain is still running [{counter}]"))
                    counter = counter + 1
            
            # Timed out
            return None

        def LangchainTimedOutSetterThread(timeout_interval_ms: int):
            time.sleep(timeout_interval_ms / 1000)
            nonlocal LangchainTimedOut
            LangchainTimedOut = True

        threading.Thread(target=LangchainTimedOutSetterThread).start()
        tmp = asyncio.run(GeneralAnalysisChainInvokation())
        
        if tmp is None:
            raise RuntimeError("Langchain Async call finished but produced absolutely nothing")

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
                        source="AI diagnos LSP",
                        tags = [
                                types.DiagnosticTag("AI")
                            ]
                        )
                    )

        _, previous = ls.diagnostics.get(document.uri, (0, []))
        
        if previous != diagnostics:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("publishing diagnostics I guess....")

            ls.diagnostics[document.uri] = (document.version, diagnostics)

            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info(f"published the following diagnostics {diagnostics} for document {document.uri}")

            ls.workspace_diagnostic_refresh(None).result()
            diagnostics_result.set_result(diagnostics)

            return logging.info("Worker thread ending")

        return logging.warning("Worker thread ending without publishing diagnostics")


    if len(document.lines) > max_file_size:
        ls.window_show_message(types.ShowMessageParams(types.MessageType(2), "File size is to big. Rejecting"))
        return

    if not time.time() - ls.last_diagnostic_time >= debounce_ms / 1000:
        ls.window_show_message(types.ShowMessageParams(types.MessageType(2), "Debounced the diagnostic"))
        return

    threading.Thread(target=BasicDiagnoseFunctionWorker).start()
    diagnostics_result.result()
    return


