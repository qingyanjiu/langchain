from langchain_openai import ChatOpenAI

def create_llm(base_url, model):
    return ChatOpenAI(
        # api_key="123",
        base_url=base_url,
        model=model,
        temperature=0,
        max_tokens=4096
    )