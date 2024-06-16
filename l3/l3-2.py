'''
FewShotPromptTemplate
'''
# 1. 创建一些示例
samples = [
  {
    "flower_type": "玫瑰",
    "occasion": "爱情",
    "ad_copy": "玫瑰，浪漫的象征，是你向心爱的人表达爱意的最佳选择。"
  },
  {
    "flower_type": "康乃馨",
    "occasion": "母亲节",
    "ad_copy": "康乃馨代表着母爱的纯洁与伟大，是母亲节赠送给母亲的完美礼物。"
  },
  {
    "flower_type": "百合",
    "occasion": "庆祝",
    "ad_copy": "百合象征着纯洁与高雅，是你庆祝特殊时刻的理想选择。"
  },
  {
    "flower_type": "向日葵",
    "occasion": "鼓励",
    "ad_copy": "向日葵象征着坚韧和乐观，是你鼓励亲朋好友的最好方式。"
  }
]

# 2. 创建一个提示模板
from langchain.prompts.prompt import PromptTemplate
template="鲜花类型: {flower_type}\n场合: {occasion}\n文案: {ad_copy}"
prompt_sample = PromptTemplate(input_variables=["flower_type", "occasion", "ad_copy"], 
                               template=template)
print(prompt_sample.format(**samples[0]))

# 3. 创建一个FewShotPromptTemplate对象
from langchain.prompts.few_shot import FewShotPromptTemplate
prompt = FewShotPromptTemplate(
    examples=samples,
    example_prompt=prompt_sample,
    suffix="鲜花类型: {flower_type}\n场合: {occasion}",
    input_variables=["flower_type", "occasion"]
)
print(prompt.format(flower_type="野玫瑰", occasion="爱情"))


'''
在这个步骤中，它首先创建了一个 SemanticSimilarityExampleSelector 对象，这个对象可以根据语义相似性选择最相关的示例。
然后，它创建了一个新的 FewShotPromptTemplate 对象，这个对象使用了上一步创建的选择器来选择最相关的示例生成提示。
然后，我们又用这个模板生成了一个新的提示，因为我们的提示中需要创建的是红玫瑰的文案，
所以，示例选择器 example_selector 会根据语义的相似度（余弦相似度）找到最相似的示例，也就是“玫瑰”，并用这个示例构建了 FewShot 模板。
这样，我们就避免了把过多的无关模板传递给大模型，以节省 Token 的用量。
'''

# pip install Chroma -i https://pypi.tuna.tsinghua.edu.cn/simple
# pip install chromadb -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 使用示例选择器
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import os

# 此处需要设置代理翻墙 huggingface你懂的。先挂v2ray代理
os.environ['https_proxy'] = 'http://localhost:10809'
# 词嵌入模型，为了转为词嵌入向量，选择与提示模板中最相似的示例
bge_embeddings = HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-zh-v1.5")

# 初始化示例选择器
example_selector = SemanticSimilarityExampleSelector.from_examples(
    samples,
    bge_embeddings,
    Chroma,
    k=1
)

# 创建一个使用示例选择器的FewShotPromptTemplate对象
prompt = FewShotPromptTemplate(
    example_selector=example_selector, 
    example_prompt=prompt_sample, 
    suffix="鲜花类型: {flower_type}\n场合: {occasion}", 
    input_variables=["flower_type", "occasion"]
)
print(prompt.format(flower_type="红玫瑰", occasion="爱情"))



# 下面调用模型，把提示传入模型，生成结果
# 实例化一个大模型工具
from langchain_community.llms import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)
result = llm.invoke(prompt.format(flower_type="野玫瑰", occasion="爱情"))
print(result)