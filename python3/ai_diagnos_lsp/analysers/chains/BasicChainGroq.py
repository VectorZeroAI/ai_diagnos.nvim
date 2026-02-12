#!/usr/bin/env python
from typing import Any, Sequence

from langchain_core.runnables import RunnableSerializable
from ai_diagnos_lsp.analysers.chains.LLM.BasicGroqLLM import BasicGroqLLMFactory
from ai_diagnos_lsp.analysers.chains.PromptObjekts.BasicAnalysisPrompt import BasicAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory

def BasicChainGroqFactory(model_groq: str, api_key_groq: str, fallback_models_groq: Sequence[str] | None = None) -> RunnableSerializable[Any, Any]:
    llm = BasicGroqLLMFactory(model_groq, api_key_groq, fallback_models_groq)
    prompt = BasicAnalysisPromptFactory()
    output = GeneralDiagnosticsOutputParserFactory()
    return prompt | llm | output
