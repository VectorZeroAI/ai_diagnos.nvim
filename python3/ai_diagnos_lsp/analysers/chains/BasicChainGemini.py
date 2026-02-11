#!/usr/bin/env python

from typing import Any
from langchain_core.runnables import RunnableSerializable


from ai_diaGeminiLlmFactoryrs.chains.LLM.BasicGeminiLLM import GeminiLlmFactory
from ai_diagnos_lsp.analysers.chains.PromptObjekts.BasicAnalysisPrompt import GeneralAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory


def BasicChainGeminiFactory(model_gemini: str, api_key_gemini: str) -> RunnableSerializable[dict[Any, Any], Any]:

    model_gemini = model_gemini
    assert model_gemini is not None
    api_key_gemini = api_key_gemini
    assert api_key_gemini is not None

    llm = GeminiLlmFactory(model_gemini, api_key_gemini)

    general_analysis_prompt = GeneralAnalysisPromptFactory()

    GeneralDiagnosticsOutputParser = GeneralDiagnosticsOutputParserFactory()

    BasicChainGemini = general_analysis_prompt | llm | GeneralDiagnosticsOutputParser

    return BasicChainGemini

