#!/usr/bin/env python3
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from lsprotocol import types
from pygls.workspace import TextDocument
import logging
import os
import threading

from ai_diagnos_lsp.analysers.chains.BasicChainGemini import BasicChainGeminiFactory
from ai_diagnos_lsp.analysers.chains.BasicChainOmniprovider import BasicChainOmniproviderFactory
from ai_diagnos_lsp.analysers.chains.BasicChainOpenrouter import BasicChainOpenrouterFactory

if TYPE_CHECKING:
    from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

def BasicDiagnoseFunctionWorker(document: TextDocument, ls: AIDiagnosLSP):
    """
    The Analyser and diagnostics provider thread . 
    """

    try:

        # ---- The section that sets up the variables.  -----

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



        # ----- registering the diagnostics to the diagnostics handling subsystem ---------




        try:
            ls.DiagnosticsHandlingSubsystem.save_new_diagnostic(diagnostics=tmp,
                                                                    document_uri=document.uri,
                                                                    analysis_type="Basic"
                                                                )
            ls.DiagnosticsHandlingSubsystem.load_diagnostics_for_file(document.uri)

        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error("Couldnt register diagnostics into Diagnostics handling subsystem")
            ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Couldnt register diagnostics due to the following reason: {e}"))
            return
        else:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("sucsessfully registered the diagnostics into the Diagnostics handling subsystem")
            return

    
    except Exception as e:
        # And error handling for the whole thread
        ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"The whole worker thread errored out with the following error: {e}"))
        return




