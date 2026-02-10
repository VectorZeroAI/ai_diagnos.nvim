#!/usr/bin/env python

from typing import List, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from pydantic import BaseModel, SecretStr
from pathlib import Path

def BasicChainOpenrouterFactory(model: str, api_key: str) -> RunnableSerializable[dict[Any, Any], Any]:

    model = model
    assert model is not None
    api_key_openrouter = api_key
    assert api_key_openrouter is not None

    Llm = ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1/",
            api_key=SecretStr(api_key_openrouter)
            )

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

