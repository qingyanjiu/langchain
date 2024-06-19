'''
输出解析器
在这里我们用到了负责数据格式验证的 Pydantic 库来创建带有类型注解的类 FlowerDescription，它可以自动验证输入数据，确保输入数据符合你指定的类型和其他验证条件。

Pydantic 有这样几个特点:
- 数据验证：当你向 Pydantic 类赋值时，它会自动进行数据验证。
    例如，如果你创建了一个字段需要是整数，但试图向它赋予一个字符串，Pydantic 会引发异常。
- 数据转换：Pydantic 不仅进行数据验证，还可以进行数据转换。
    例如，如果你有一个需要整数的字段，但你提供了一个可以转换为整数的字符串，如 "42"，Pydantic 会自动将这个字符串转换为整数 42。
- 易于使用：创建一个 Pydantic 类就像定义一个普通的 Python 类一样简单。只需要使用 Python 的类型注解功能，即可在类定义中指定每个字段的类型。
- JSON 支持：Pydantic 类可以很容易地从 JSON 数据创建，并可以将类的数据转换为 JSON 格式。
'''

# 实例化一个大模型工具
from langchain_community.llms.ollama import Ollama
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
    reason: str = Field(description="the reason for your choice, in Chinese")


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
对于售价为 {price} 元的 {flower} ，您能提供一个吸引人的简短中文描述吗？不要包含'['和']'字符
{format_instructions}"""

# 根据模板创建提示，同时在提示中加入输出解析器的说明
prompt = PromptTemplate.from_template(prompt_template, 
        partial_variables={"format_instructions": format_instructions})

# 打印提示
# print("提示：", prompt)
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

    # 解析模型的输出
    parsed_output = output_parser.parse(out_str)

    # 将Pydantic格式转换为字典
    parsed_output_dict = parsed_output.model_dump()

    # 将解析后的输出添加到DataFrame中
    df.loc[len(df)] = parsed_output.model_dump()

# 打印字典
print("输出的数据：", df.to_dict(orient='records'))