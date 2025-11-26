from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

def openai_llm(base_url, model) -> BaseChatModel:
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        temperature=0,
        max_tokens=4096
    )