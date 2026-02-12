from typing import Sequence, Any
from langchain_core.runnables import RunnableWithFallbacks
from langchain_groq import ChatGroq
from pydantic import SecretStr

def BasicGroqLLMFactory(model_groq: str,  api_key_groq: str, fallback_models_groq: Sequence[str] | None = None) -> ChatGroq | RunnableWithFallbacks[Any, Any]:
    """
    This is the Langchain llm objekt Factory function for the Groq provider.
    It can produce both an llm for only one model, or an llm for many models . 
    """
    llm = ChatGroq(
            model=model_groq,
            api_key=SecretStr(api_key_groq),
            max_retries=0,
            )
    if fallback_models_groq is not None:
        fallback_llms = []
        for i in fallback_models_groq:
            fallback_llms.append(
                    ChatGroq(
                        api_key=SecretStr(api_key_groq),
                        model=i,
                        max_retries=0
                    )
                )
        llm = llm.with_fallbacks(fallback_llms)
    else:
        pass
    return llm
