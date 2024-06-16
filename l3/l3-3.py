'''
How to use few shot examples in chat models
'''
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

examples = [
    {"input": "一只青蛙1张嘴，2只眼睛,4条腿，2只青蛙几个眼睛?", "output": "4"},
    {"input": "一只青蛙1张嘴，2只眼睛,4条腿，3只青蛙几条腿？", "output": "12"},
]

# This is a prompt template used to format each individual example.
example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "{input}"),
        ("ai", "{output}"),
    ]
)
few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)



final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个懂算数的人,请直接给出数字答案"),
        few_shot_prompt,
        ("human", "{input}"),
    ]
)

# 实例化一个大模型工具
from langchain_community.llms import Ollama

chain = final_prompt | Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.0)

print(chain.invoke({"input": "20只青蛙几个眼睛？"}))