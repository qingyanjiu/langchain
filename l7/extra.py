'''
多模态
'''
import base64
from io import BytesIO
from PIL import Image


def convert_to_base64(pil_image):
    """
    Convert PIL images to Base64 encoded strings

    :param pil_image: PIL image
    :return: Re-sized Base64 string
    """

    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")  # You can change the format if needed
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

file_path = "l7/1.png"
pil_image = Image.open(file_path)
image_b64 = convert_to_base64(pil_image)

# 实例化一个大模型工具
from langchain_community.llms.ollama import Ollama
bakllava = Ollama(base_url='http://localhost:11434', model="bakllava", temperature=0.2)

llm_with_image_context = bakllava.bind(images=[image_b64])
res = llm_with_image_context.invoke("Is there any one smoking?")

# llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0)
# from langchain.prompts import PromptTemplate
# prompt = PromptTemplate.from_template('''
# 请将下面的文本翻译成中文:{text}                               )
# ''')
# res = llm.invoke(prompt.format(text=res))

print(res)