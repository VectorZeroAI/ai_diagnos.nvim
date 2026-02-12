#!/usr/bin/env python

from typing import Any, Sequence
from langchain_core.runnables import RunnableSerializable


from ai_diagnos_lsp.analysers.chains.LLM.BasicGeminiLLM import GeminiLlmFactory
from ai_diagnos_lsp.analysers.chains.PromptObjekts.BasicAnalysisPrompt import BasicAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory


def BasicChainGeminiFactory(model_gemini: str, api_key_gemini: str, fallback_models_gemini: Sequence[str] | None = None) -> RunnableSerializable[dict[Any, Any], Any]:
    """
    This is the Gemini langchain chain Factory function. 
    Its my style to make Factory functions for parts, even if it is a bit uselles. 
    """

    model_gemini = model_gemini
    api_key_gemini = api_key_gemini

    if fallback_models_gemini is not None:
        llm = GeminiLlmFactory(model_gemini, api_key_gemini, fallback_models_gemini)
    else:
        llm = GeminiLlmFactory(model_gemini, api_key_gemini)

    general_analysis_prompt = BasicAnalysisPromptFactory()

    GeneralDiagnosticsOutputParser = GeneralDiagnosticsOutputParserFactory()

    BasicChainGemini = general_analysis_prompt | llm | GeneralDiagnosticsOutputParser

    return BasicChainGemini

