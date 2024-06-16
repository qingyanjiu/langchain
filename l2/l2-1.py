'''
提示词模板
'''
# 导入LangChain中的提示模板
from langchain.prompts import PromptTemplate
# 创建原始模板
template = """您是一位专业的鲜花店文案撰写员。\n
对于售价为 {price} 元的 {flower_name} ，您能提供一个吸引人的简短描述吗？
"""
# 根据原始模板创建LangChain提示模板
prompt = PromptTemplate.from_template(template) 
# 打印LangChain提示模板的内容
print(prompt)


# 创建模型实例
import logging # 导入Logging工具
from langchain_community.llms import Ollama

# 设置Logging
logging.basicConfig()
logging.getLogger('langchain.retrievers.multi_query').setLevel(logging.INFO)

# 实例化一个大模型工具
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)

# 多种花的列表
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]

# 生成多种花的文案
for flower, price in zip(flowers, prices):
    # 使用提示模板生成输入 
    input_prompt = prompt.format(flower_name=flower, price=price)

    output = llm.invoke(input_prompt)
    # 打印输出内容 
    print(output)