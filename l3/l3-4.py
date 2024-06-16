'''
Dynamic few-shot prompting
'''
from langchain_chroma import Chroma
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import os

examples = [
    {"input": "2+2", "output": "4"},
    {"input": "2+3", "output": "5"},
    {"input": "2+4", "output": "6"},
    {"input": "What did the cow say to the moon?", "output": "nothing at all"},
    {
        "input": "Write me a poem about the moon",
        "output": "One for the moon, and one for me, who are we to talk about the moon?",
    },
]

to_vectorize = [" ".join(example.values()) for example in examples]

# 此处需要设置代理翻墙 huggingface你懂的。先挂v2ray代理
os.environ['https_proxy'] = 'http://localhost:10809'

# 词嵌入模型，为了转为词嵌入向量，选择与提示模板中最相似的示例
embeddings = HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-zh-v1.5")
vectorstore = Chroma.from_texts(to_vectorize, embeddings, metadatas=examples)

example_selector = SemanticSimilarityExampleSelector(
    vectorstore=vectorstore,
    k=1,
)

# The prompt template will load examples by passing the input do the `select_examples` method
print("测试词嵌入匹配  -- ", example_selector.select_examples({"input": "测试词嵌入匹配"}))



from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

# Define the few-shot prompt.
few_shot_prompt = FewShotChatMessagePromptTemplate(
    # The input variables select the values to pass to the example_selector
    input_variables=["input"],
    example_selector=example_selector,
    # Define how each example will be formatted.
    # In this case, each example will become 2 messages:
    # 1 human, and 1 AI
    example_prompt=ChatPromptTemplate.from_messages(
        [("human", "{input}"), ("ai", "{output}")]
    ),
)

# print(few_shot_prompt.invoke(input="What's 3+3?").to_messages())

final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a wondrous wizard of math."),
        few_shot_prompt,
        ("human", "{input}"),
    ]
)

# print(few_shot_prompt.invoke(input="What's 3+3?"))

# 实例化一个大模型工具
from langchain_community.llms import Ollama

chain = final_prompt | Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.0)

print(chain.invoke({"input": "What's 3+3?"}))