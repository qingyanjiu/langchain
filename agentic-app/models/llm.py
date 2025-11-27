from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel

def openai_llm(base_url, model) -> BaseLanguageModel:
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        temperature=0,
        max_tokens=4096
    )