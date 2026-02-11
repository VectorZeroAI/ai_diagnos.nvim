#!/usr/bin/env python


from typing import Any

from langchain_core.runnables import RunnableSerializable

from ai_diagnos_lsp.analysers.chains.BasicChainOpenrouter import OpenrouterLlmFactory
from ai_diagnos_lsp.analysers.chains.BasicChainGemini import GeminiLlmFactory

def BasicChainOmniproviderFactory(api_key_openrouter: str, api_key_gemini: str, model_openrouter: str, model_gemini: str) -> RunnableSerializable[dict[Any, Any], Any]: 
    OmniproviderLLM = OpenrouterLlmFactory(model_openrouter, api_key_openrouter
                                           ).with_fallbacks([
                                               GeminiLlmFactory(model_gemini, api_key_gemini)
                                               ])
    BasicChainOmniprovider = 
