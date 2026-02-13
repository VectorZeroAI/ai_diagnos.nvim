#!/usr/bin/env python
from typing import Sequence, Any
from langchain_core.runnables import RunnableWithFallbacks
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr
import logging
import os

def GeminiLlmFactory(model_gemini: str, api_key_gemini: str,
                     fallback_gemini_models: Sequence[str] | None = None
                     ) -> ChatGoogleGenerativeAI | RunnableWithFallbacks[Any, Any]:
    """
    This is the Langchain llm objekt Factory function for the Gemini provider.
    It can produce both an llm for only one model, or an llm for many models . 
    """


    llm = ChatGoogleGenerativeAI(
            model=model_gemini,
            api_key=SecretStr(api_key_gemini), max_retries=1
            )

    if fallback_gemini_models is not None:
        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info(f" fallback gemini llms gotten by GeminiLlm Factory. Gotten : {fallback_gemini_models} ")

        fallback_llms_list = []
        for i in fallback_gemini_models:
            tmp_llm = ChatGoogleGenerativeAI(
                    model=i,
                    api_key=SecretStr(api_key_gemini), max_retries=1
                    )
            fallback_llms_list.append(tmp_llm)
        llm = llm.with_fallbacks(fallback_llms_list)

    return llm
