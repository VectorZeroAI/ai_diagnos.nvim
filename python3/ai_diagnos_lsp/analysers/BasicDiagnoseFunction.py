import time
from typing import Tuple
from lsprotocol import types
from pygls.workspace import TextDocument
import logging
import os
import threading

from ai_diagnos_lsp.analysers.chains.BasicChainGemini import BasicChainGeminiFactory
from ai_diagnos_lsp.analysers.chains.BasicChainOmniprovider import BasicChainOmniproviderFactory
from ai_diagnos_lsp.analysers.chains.BasicChainOpenrouter import BasicChainOpenrouterFactory

from ai_diagnos_lsp.utils.grep import grep

from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

def BasicDiagnoseFunctionWorker(document: TextDocument, ls: AIDiagnosLSP):
    """
    The Analyser and diagnostics provider thread . 
    """

    try:

        # ---- The section that sets up the variables.  -----

        diagnostics = []

        severity_map = {
                1: types.DiagnosticSeverity.Error,
                2: types.DiagnosticSeverity.Warning,
                3: types.DiagnosticSeverity.Information,
                4: types.DiagnosticSeverity.Hint
                }

        debounce_ms = ls.config["debounce_ms"]

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f"recieved = {debounce_ms}")
        
        show_progress_every_ms = ls.config["show_progress_every_ms"]

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f"recieved = {show_progress_every_ms}")

        show_progress = ls.config["show_progress"]

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f"recieved = {show_progress}")

        max_file_size = ls.config["max_file_size"]

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f"recieved = {max_file_size}")


        timeout = ls.config["timeout"]

        ls.window_show_message(types.ShowMessageParams(types.MessageType(3), f"The timeout recieved is the following : {timeout}"))


        
        #  ------- The Basic Chain setup section --------



        if ls.config["use_omniprovider"]:

            BasicChain = BasicChainOmniproviderFactory(
                    model_openrouter=ls.config["model_openrouter"],
                    api_key_openrouter=ls.config["api_key_openrouter"],
                    api_key_gemini=ls.config["api_key_gemini"],
                    model_gemini=ls.config["model_gemini"],
                    fallback_models_gemini=ls.config.get("fallback_models_gemini"),
                    api_key_groq=ls.config["api_key_groq"],
                    model_groq=ls.config["model_groq"],
                    fallback_models_groq=ls.config.get("fallback_models_groq")
                    )

        elif ls.config["use_gemini"]:

            BasicChain = BasicChainGeminiFactory(
                    api_key_gemini=ls.config["api_key_gemini"],
                    model_gemini=ls.config["model_gemini"],
                    fallback_models_gemini=ls.config.get("fallback_models_gemini")
                    )

        elif ls.config["use_openrouter"]:
            BasicChain = BasicChainOpenrouterFactory(
                    model_openrouter=ls.config["model_openrouter"],
                    api_key_openrouter=ls.config["api_key_openrouter"]
                    )
        else:
            ls.window_show_message(types.ShowMessageParams(types.MessageType(1), "INVALID CONFIGURATION RECIEVED. One of use parameters must be true !"))
            raise RuntimeError("INVALID CONFIGURATION RECIEVED. One of use parameters must be true !")
            


        # ------- The chain invokation part.  -------
        # It functions kinda like this: 
        # It sets up a bunch of events
        # Then it starts the chain onvokation in a separate thread. 
        # Then it also starts a thread that pings the user that the server is doing something
        # Then it just checks for timeout, as well as for faliure.  Thats it. 


        langchain_completed_event = threading.Event()
        langchain_timed_out = threading.Event()
        langchain_failed = threading.Event()

        tmp = None

        def LangchainInvokingThread(document: TextDocument):
            try:
                nonlocal tmp
                tmp = BasicChain.invoke({
                    "file_content": document.source
                    })
                langchain_completed_event.set()
            except Exception as e:
                ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Langchain invoking thread errored out with the following error : {e}"))
                langchain_completed_event.set()
                langchain_failed.set()

        threading.Thread(target=LangchainInvokingThread, args=(document,), daemon=True).start()

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("starting the chain")
            logging.info(f"chain started with input document as {document.source}")

        def LangchainStillRunningPingerThread(ls, show_progress_every_ms: int):
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("Langchain Pinger thread started")

            counter = 1

            while not (langchain_completed_event.is_set() or langchain_timed_out.is_set()):
                ls.window_show_message(types.ShowMessageParams(types.MessageType(3), f"Langchain still running [{counter}]"))
                counter = counter + 1
                time.sleep(show_progress_every_ms / 1000)
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("Langchain is still running")

            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("Langchain Pinger thread exited")
                
        if show_progress:
            threading.Thread(target=LangchainStillRunningPingerThread, args=(ls, show_progress_every_ms), daemon=True).start()

        if timeout > threading.TIMEOUT_MAX:
            timeout = threading.TIMEOUT_MAX
            
        if langchain_completed_event.wait(timeout):
            pass
        else:
            ls.window_show_message(types.ShowMessageParams(types.MessageType(2), "Langchain timed out"))
            return

        if langchain_failed.is_set():
            ls.window_show_message(types.ShowMessageParams(types.MessageType(1), "Langchain FAILED"))
            return




        # --------- The diagnostics handling section -----------



        for i in tmp.diagnostics:
            try:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("searching the file with grep. ")
                    logging.info(f"searching for : {i.location} ; in {document.uri}")
                
                if isinstance(i.location, Tuple):
                    pos = grep(i.location[0], document.source)[i.location[1] - 1]
                else:
                    pos = grep(i.location, document.source)[0]
                pos_line = pos[0]
                pos_char = pos[1]
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info(f"found {i.location} at line : {pos_line}, char : {pos_char}")
            except IndexError as e:
                # Ignore the diagnostic entirely, because if no matches were found, it means that the AI
                # halucinated, wich makes this one specific diagnostic is wrong, wich is not worth the hassle
                # to try to use. So it is skipped. This is by design, not an error. 

                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info(f"Errored out. Most likely a halucinated citation. The error : {e}")
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
                        source="AI diagnos LSP", data="AI",code="AI",
                        code_description=types.CodeDescription(" This is AI generated Diagnostics. I am putting this wherever I can because why not ?  ")
                        )
                    )



        # -------- The diagnostics publishing section ------------
        # Also the last section of the thread. 




        _, previous = ls.diagnostics.get(document.uri, (0, []))
        
        if previous != diagnostics:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("publishing diagnostics I guess....")

            with ls.diagnostics_lock:
                ls.diagnostics[document.uri] = (document.version, diagnostics)

            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info(f"published the following diagnostics {diagnostics} for document {document.uri}")

            ls.workspace_diagnostic_refresh(None).result()

            return logging.info("Worker thread ending")

        return logging.warning("Worker thread ending without publishing diagnostics")

    
    except Exception as e:
        # And error handling for the whole thread
        ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"The whole worker thread errored out with the following error: {e}"))
        return




