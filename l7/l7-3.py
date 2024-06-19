'''
自动修复解析器（OutputFixingParser）

'''

# 实例化一个大模型工具
from langchain_community.llms import Ollama
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)

# ------Part 2
# 创建一个空的DataFrame用于存储结果
import pandas as pd
df = pd.DataFrame(columns=["flower_type", "price", "description", "reason"])

# 数据准备
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]

# 定义我们想要接收的数据格式
from pydantic import BaseModel, Field
class FlowerDescription(BaseModel):
    # 这里description用英文效果会比较好
    flower_type: str = Field(description="flower type")
    price: int = Field(description="price")
    description: str = Field(description="description of the flower, in Chinese, do not in English")
    reason: str = Field(description="the reason for your choice, in Chinese, do not in English")


# ------Part 3
# 创建输出解析器
from langchain.output_parsers import PydanticOutputParser
output_parser = PydanticOutputParser(pydantic_object=FlowerDescription)

# 获取输出格式指示
format_instructions = output_parser.get_format_instructions()
# 打印提示
# print("输出格式：",format_instructions)

# ------Part 4
# 创建提示模板
from langchain.prompts import PromptTemplate
prompt_template = """您是一位专业的鲜花店文案撰写员。
对于售价为 {price} 元的 {flower} ，您能提供一个吸引人的简短中文描述吗？
{format_instructions}"""

# 根据模板创建提示，同时在提示中加入输出解析器的说明
prompt = PromptTemplate.from_template(prompt_template, 
        partial_variables={"format_instructions": format_instructions})

# 打印提示
# print("提示：", prompt)

from langchain.output_parsers.retry import RetryWithErrorOutputParser

# 使用OutputFixingParser创建一个新的解析器，该解析器能够纠正格式不正确的输出
retry_parser = RetryWithErrorOutputParser.from_llm(parser=output_parser, llm=llm)

import json

# ------Part 5
for flower, price in zip(flowers, prices):
    # 根据提示准备模型的输入
    input = prompt.format(flower=flower, price=price)
    # 打印提示
    # print("提示：", input)

    # 获取模型的输出
    output = llm.invoke(input)

    out_json = json.loads(output)
    if (out_json.get('properties')):
        out_str = json.dumps(out_json['properties'])
    else:
        out_str = output

    # 自动修复有问题的输出
    parsed_output = retry_parser.parse_with_prompt(out_str, input)

    # 将Pydantic格式转换为字典
    parsed_output_dict = parsed_output.model_dump()

    # 将解析后的输出添加到DataFrame中
    df.loc[len(df)] = parsed_output_dict

# 打印字典
print("输出的数据：", df.to_dict(orient='records'))