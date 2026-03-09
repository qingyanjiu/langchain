from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    model="qwen/qwen3-vl-8b",
    openai_api_key="sk-mzwqslirxtrhdtcdwqpdizesufygfocxjckbpehzslsrtass",
    openai_api_base="http://192.168.100.85:1234/v1",
    temperature=0
)

message = HumanMessage(
    content=[
        {"type": "text", "text": "请详细描述图片内容"},
        {
            "type": "image_url",
            "image_url": {
                "url": "http://localhost:555/ComfyUI_00016_.png"
            }
        }
    ]
)

res = llm.invoke([message])
print(res.content)