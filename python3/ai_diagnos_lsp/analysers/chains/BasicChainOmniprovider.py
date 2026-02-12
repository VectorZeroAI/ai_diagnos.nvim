#!/usr/bin/env python

from typing import Any, Sequence

from langchain_core.runnables import RunnableSerializable

from ai_diagnos_lsp.analysers.chains.LLM.BasicOpenrouterLLM import OpenrouterLlmFactory
from ai_diagnos_lsp.analysers.chains.LLM.BasicGeminiLLM import GeminiLlmFactory
from ai_diagnos_lsp.analysers.chains.LLM.BasicGroqLLM import BasicGroqLLMFactory

from ai_diagnos_lsp.analysers.chains.PromptObjekts.BasicAnalysisPrompt import BasicAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory
import os

import logging

def BasicChainOmniproviderFactory(api_key_openrouter: str,
                                  api_key_gemini: str,
                                  api_key_groq: str,
                                  model_openrouter: str,
                                  model_gemini: str,
                                  model_groq: str,
                                  fallback_models_gemini: Sequence[str] | None = None,
                                  fallback_models_groq: Sequence[str] | None = None
                                  ) -> RunnableSerializable[Any, Any]: 

#    if fallback_models_gemini is not None:
#        if os.getenv("AI_DIAGNOS_LOG") is not None:
#            logging.info(f"gemini fallback models gotten by BasicChainOmniproviderFactory. Gotten : {fallback_models_gemini}")
#
#        OmniproviderLLM = OpenrouterLlmFactory(model_openrouter, api_key_openrouter
#                                               ).with_fallbacks([
#                                                   GeminiLlmFactory(model_gemini, api_key_gemini, fallback_models_gemini)
#                                                   ])
#    else:
#        if os.getenv("AI_DIAGNOS_LOG") is not None:
#            logging.warning("gemini fallback models NOT gotten. ")
#        OmniproviderLLM = OpenrouterLlmFactory(model_openrouter, api_key_openrouter
#                                               ).with_fallbacks([
#                                                   GeminiLlmFactory(model_gemini, api_key_gemini)
#                                                   ])

    llm = OpenrouterLlmFactory(model_openrouter, api_key_openrouter)
    fallbacks = []
    if fallback_models_gemini is not None:
        fallbacks.append(GeminiLlmFactory(model_gemini, api_key_gemini, fallback_models_gemini))
    else:
        fallbacks.append(GeminiLlmFactory(model_gemini, api_key_gemini))

    if fallback_models_groq is not None:
        fallbacks.append(BasicGroqLLMFactory(model_groq, api_key_groq, fallback_models_groq))
    else:
        fallbacks.append(BasicGroqLLMFactory(model_groq, api_key_groq))

    llm = llm.with_fallbacks(fallbacks)


    prompt = BasicAnalysisPromptFactory()
    output_parser = GeneralDiagnosticsOutputParserFactory()

    basic_chain_omniprovider = prompt | llm | output_parser
    return basic_chain_omniprovider
