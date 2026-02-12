#!/usr/bin/env python

from typing import Any, Sequence

from langchain_core.runnables import RunnableSerializable

from ai_diagnos_lsp.analysers.chains.LLM.BasicOpenrouterLLM import OpenrouterLlmFactory
from ai_diagnos_lsp.analysers.chains.LLM.BasicGeminiLLM import GeminiLlmFactory
from ai_diagnos_lsp.analysers.chains.LLM.BasicGroqLLM import BasicGroqLLMFactory

from ai_diagnos_lsp.analysers.chains.PromptObjekts.BasicAnalysisPrompt import BasicAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory

def BasicChainOmniproviderFactory(api_key_openrouter: str,
                                  api_key_gemini: str,
                                  api_key_groq: str,
                                  model_openrouter: str,
                                  model_gemini: str,
                                  model_groq: str,
                                  fallback_models_gemini: Sequence[str] | None = None,
                                  fallback_models_groq: Sequence[str] | None = None
                                  ) -> RunnableSerializable[Any, Any]: 
    """
    This is Chain Creation function for the Omniprovider option, e.g. for everyone
    It falls back through providers in order of Openrouter -> Gemini -> Groq 
    Why ? IDK . 
    
    So it basically just chains the chains in the fallback options, so that every provider is used. 
    """

    # TODO : ADD logging back in

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
