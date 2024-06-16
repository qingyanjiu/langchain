'''
ChatPromptTemplate 多角色promptTemplate
'''
# 导入聊天消息类模板
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
# 模板的构建
template="你是一位专业顾问，负责为专注于为{product}公司起简体中文的名称。只给出名称,不需要输出其他信息。"
system_message_prompt = SystemMessagePromptTemplate.from_template(template)
human_template="公司主打产品是{product_detail}。"
human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
prompt_template = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

# 格式化提示消息生成提示
prompt = prompt_template.format_prompt(product="鲜花装饰", product_detail="创新的鲜花设计。").to_messages()

# 下面调用模型，把提示传入模型，生成结果
# 实例化一个大模型工具
from langchain_community.llms import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)
result = llm.invoke(prompt)
print(result)