#!/usr/bin/env python
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

def BasicAnalysisPromptFactory() -> ChatPromptTemplate:
    """
    This is the Prompt Objekt factory for the chain.
    I cant make it just an importable class, because if I do, 
    I would still have to make an instanse of it for it to actually read the prompt. 
    The prompt is stored in a separate file, at the prompts directory. 
    """

    try:
        with open(f"{Path(__file__).absolute().resolve().parent}/../prompts/general_analysis_system_prompt.txt", "r") as f:
            GENERAL_ANALYSIS_SYSTEM_PROMPT = f.read()
    except FileNotFoundError as e:
        raise NotImplementedError("The prompt file is missing.") from e

    GeneralAnalysisPrompt = ChatPromptTemplate.from_messages([
            ("system", f"{GENERAL_ANALYSIS_SYSTEM_PROMPT}"),
            ("human", "\n{{file_content}}\n\n"),
            ], template_format="mustache")
    return GeneralAnalysisPrompt
