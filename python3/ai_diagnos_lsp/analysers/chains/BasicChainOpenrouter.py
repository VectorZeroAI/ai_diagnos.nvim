#!/usr/bin/env python

from typing import List, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from pydantic import BaseModel
from pathlib import Path

from ai_diagnos_lsp.analysers.chains.LLM.BasicOpenrouterLLM import OpenrouterLlmFactory


def BasicChainOpenrouterFactory(model_openrouter: str, api_key_openrouter: str) -> RunnableSerializable[dict[Any, Any], Any]:

    Llm = OpenrouterLlmFactory(model_openrouter, api_key_openrouter)

    try:
        with open(f"{Path(__file__).absolute().resolve().parent}/prompts/general_analysis_system_prompt.txt", "r") as f:
            GENERAL_ANALYSIS_SYSTEM_PROMPT = f.read()
    except FileNotFoundError as e:
        raise NotImplementedError("The prompt file is missing.") from e

    GeneralAnalysisPrompt = ChatPromptTemplate.from_messages([
            ("system", f"{GENERAL_ANALYSIS_SYSTEM_PROMPT}"),
            ("human", "\n{{file_content}}\n\n"),
            ], template_format="mustache")

    class DiagnosticsPydanticObjekt(BaseModel):
        class SingleDiagnostic(BaseModel):

            location: str
            error_message: str
            severity_level: int

            # TODO : Double check if this is enough

        class Config:
            populate_by_name = True

        diagnostics: List[SingleDiagnostic]

    GeneralDiagnosticsOutputParser = PydanticOutputParser(pydantic_object=DiagnosticsPydanticObjekt)

    BasicChainOpenrouter = GeneralAnalysisPrompt | Llm | GeneralDiagnosticsOutputParser

    return BasicChainOpenrouter

