'''
ReAct 框架
ReAct 框架的灵感正是来自“行动”和“推理”之间的协同作用，这种协同作用使得咱们人类能够学习新任务并做出决策或推理。
这个框架，也是大模型能够作为“智能代理”，自主、连续、交错地生成推理轨迹和任务特定操作的理论基础。

在开始之前，有一个准备工作，就是你需要在 serpapi.com 注册一个账号，并且拿到你的 SERPAPI_API_KEY，这个就是我们要为大模型提供的 Google 搜索工具
serpapi免费额度太少了
改用微软 Azure Bing Search service
'''

from langchain_core.tools import tool, StructuredTool
from langchain.pydantic_v1 import BaseModel, Field

class CalculatorInput(BaseModel):
    exp: str = Field(description="expression")

# 自定义tool
@tool("my_calc", args_schema=CalculatorInput, return_direct=True)
def my_calc(exp: str) -> float:
    """calculate"""
    exp = exp.replace('=', '')
    return eval(exp)

my_multiply = StructuredTool.from_function(
    func=my_calc,
    name="my_multiply",
    description="multiply numbers",
    args_schema=CalculatorInput,
    return_direct=True,
    # coroutine= ... <- you can specify an async method if desired as well
)

# print(my_calc.name)
# print(my_calc.description)
# print(my_calc.args)
# print(my_calc.return_direct)

# 初始化大语言模型
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)

import os

os.environ["BING_SUBSCRIPTION_KEY"] = '362c8a355c884169b930183a7b481b83'
os.environ["BING_SEARCH_URL"] = "https://api.bing.microsoft.com/v7.0/search"

from langchain_community.utilities import BingSearchAPIWrapper
from langchain_community.tools.bing_search import BingSearchResults
from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType

search_wrapper = BingSearchAPIWrapper(k=1)

# 测试bing搜索api
# result = search_wrapper.run("python")
# print(result)

tool = BingSearchResults(api_wrapper=search_wrapper)
# pip install numexpr -i https://pypi.tuna.tsinghua.edu.cn/simple
# 使用默认llm-math数学函数，有时候计算会报错
# tools = load_tools(["bing-search", "llm-math"], llm=llm)

# 尝试使用自定义计算
tools = load_tools(["bing-search"], llm=llm)
tools.append(my_calc)

agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
result = agent.invoke('''2024年6月30日淘宝iphone15的价格是多少?如果我在此基础上加价15%卖出，应该如何定价？''')
# result = agent.invoke("鸡肉亲子盖饭的原料有哪些？")
# result = agent.invoke("7月1日欧洲杯有哪些比赛？")
print(result)