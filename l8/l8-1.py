'''
用SequencialChain链接不同的组件
'''

#----第一步 创建提示
# 导入LangChain中的提示模板
from langchain.prompts import PromptTemplate
# 原始字符串模板
template = "{flower}的花语是?"
# 创建LangChain模板
prompt_temp = PromptTemplate.from_template(template) 
# 根据模板创建提示
prompt = prompt_temp.format(flower='玫瑰')
# 打印提示的内容
print(prompt)

#----第二步 创建并调用模型 
# 实例化一个大模型工具
from langchain_community.llms.ollama import Ollama
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)
# 传入提示，调用模型，返回结果
# result = llm.invoke(prompt)
# print(result)


# ===========================

from langchain.chains.llm import LLMChain
# 创建LLMChain
llm_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate.from_template(template))
# 调用LLMChain，返回结果
result = llm_chain.generate([{"flower": "玫瑰"}])
print(result)