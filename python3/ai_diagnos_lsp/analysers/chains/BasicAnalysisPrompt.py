
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

def GeneralAnalysisPromptFactory() -> ChatPromptTemplate:
    try:
        with open(f"{Path(__file__).absolute().resolve().parent}/prompts/general_analysis_system_prompt.txt", "r") as f:
            GENERAL_ANALYSIS_SYSTEM_PROMPT = f.read()
    except FileNotFoundError as e:
        raise NotImplementedError("The prompt file is missing.") from e

    GeneralAnalysisPrompt = ChatPromptTemplate.from_messages([
            ("system", f"{GENERAL_ANALYSIS_SYSTEM_PROMPT}"),
            ("human", "\n{{file_content}}\n\n"),
            ], template_format="mustache")
    return GeneralAnalysisPrompt
