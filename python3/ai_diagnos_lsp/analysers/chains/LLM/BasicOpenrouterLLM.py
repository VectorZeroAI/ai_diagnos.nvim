#!/usr/bin/env python
from langchain_openai import ChatOpenAI

from pydantic import SecretStr

def OpenrouterLlmFactory(model_openrouter: str, api_key_openrouter: str) -> ChatOpenAI:
    """
    This is the Langchain llm objekt Factory function for the Openrouter provider.
    It can not be created with fallback models due to how openrouter counts ratelimits. 
    They are per key / account, not per model, so it would be utterly uselles. 
    """
    llm = ChatOpenAI(
            model=model_openrouter,
            base_url="https://openrouter.ai/api/v1/",
            api_key=SecretStr(api_key_openrouter),
            max_retries=0
            )
    return llm
