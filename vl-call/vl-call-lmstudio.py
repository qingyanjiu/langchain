import base64
import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from PIL import Image
import io


# LM Studio API
llm = ChatOpenAI(
    base_url="http://192.168.100.85:1234/v1",
    api_key="lm-studio",
    model="qwen3-vl-8b"
)


# 压缩 PIL Image 并转 base64
def resize_image(img: Image.Image, size=1024):
    img = img.copy()
    img.thumbnail((size, size))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)

    return base64.b64encode(buf.getvalue()).decode()


# 从本地路径读取图片
def resize_image_with_path(path, size=1024):
    img = Image.open(path)
    return resize_image(img, size)


# URL → 下载 → PIL Image → base64
def url_to_data_uri(url: str):
    resp = requests.get(url)
    resp.raise_for_status()

    img_bytes = resp.content
    img = Image.open(io.BytesIO(img_bytes))

    return resize_image(img)


# 自动处理 URL / 本地图片
def normalize_image(img):
    if img.startswith("http"):
        b64 = url_to_data_uri(img)
    else:
        b64 = resize_image_with_path(img)

    return f"data:image/jpeg;base64,{b64}"


# 测试图片
image_url = "http://localhost:555/ComfyUI_00016_.png"

image_data = normalize_image(image_url)


message = HumanMessage(
    content=[
        {"type": "text", "text": "请描述这张图片"},
        {
            "type": "image_url",
            "image_url": {
                "url": image_data
            },
        },
    ]
)


res = llm.invoke([message])

print(res.content)