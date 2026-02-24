from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    model="Qwen/Qwen3-VL-8B-Thinking",
    openai_api_key="sk-mzwqslirxtrhdtcdwqpdizesufygfocxjckbpehzslsrtass",
    openai_api_base="https://api.siliconflow.cn/v1",
    temperature=0
)

message = HumanMessage(
    content=[
        {"type": "text", "text": "请详细描述图片内容"},
        {
            "type": "image_url",
            "image_url": {
                "url": "http://107.173.83.242:35555/ComfyUI_00022_.png"
            }
        }
    ]
)

res = llm.invoke([message])
print(res.content)