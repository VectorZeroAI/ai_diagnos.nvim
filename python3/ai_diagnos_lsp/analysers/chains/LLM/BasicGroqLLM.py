from typing import Sequence, Any
from langchain_core.runnables import RunnableWithFallbacks
from langchain_groq import ChatGroq
from pydantic import SecretStr

def BasicGroqLLMFactory(model_groq: str,  api_key_groq: str, fallback_models_groq: Sequence[str] | None = None) -> ChatGroq | RunnableWithFallbacks[Any, Any]:
    llm = ChatGroq(
            model=model_groq,
            api_key=SecretStr(api_key_groq)
            )
    if fallback_models_groq is not None:
        fallback_llms = []
        for i in fallback_models_groq:
            fallback_llms.append(
                    ChatGroq(
                        api_key=SecretStr(api_key_groq),
                        model=i
                    )
                )
        llm = llm.with_fallbacks(fallback_llms)
    else:
        pass
    return llm
