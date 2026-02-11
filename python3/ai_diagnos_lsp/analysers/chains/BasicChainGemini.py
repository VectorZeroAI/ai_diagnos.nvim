#!/usr/bin/env python

from typing import List, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_google_genai import ChatGoogleGenerativeAI

from pydantic import BaseModel, SecretStr
from pathlib import Path

from ai_diagnos_lsp.analysers.chains.BasicAnalysisPrompt import GeneralAnalysisPromptFactory
from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsOutputParserFactory

def GeminiLlmFactory(model_gemini: str, api_key_gemini: str) -> ChatGoogleGenerativeAI:
    llm = ChatGoogleGenerativeAI(
            model=model_gemini,
            api_key=SecretStr(api_key_gemini),
            )
    return llm
    

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

