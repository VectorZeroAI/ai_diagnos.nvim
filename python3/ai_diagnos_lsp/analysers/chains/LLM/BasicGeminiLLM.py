#!/usr/bin/env python
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr
    
def GeminiLlmFactory(model_gemini: str, api_key_gemini: str) -> ChatGoogleGenerativeAI:
    llm = ChatGoogleGenerativeAI(
            model=model_gemini,
            api_key=SecretStr(api_key_gemini),
            )
    return llm
