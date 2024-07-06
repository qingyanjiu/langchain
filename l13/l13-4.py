'''
计划和执行代理通过首先计划要做什么，然后执行子任务来实现目标。
这个想法是受到 Plan-and-Solve 论文的启发。论文中提出了计划与解决（Plan-and-Solve）提示。
它由两部分组成：首先，制定一个计划，并将整个任务划分为更小的子任务；然后按照该计划执行子任务。
这种代理的独特之处在于，它的计划和执行不再是由同一个代理所完成，而是：
计划由一个大语言模型代理（负责推理）完成。
执行由另一个大语言模型代理（负责调用工具）完成。

pip install -U langchain langchain_experimental -i https://pypi.tuna.tsinghua.edu.cn/simple
'''

# 初始化大语言模型
import os
from langchain_community.llms.ollama import Ollama
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0)
llm_1 = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)

# 讯飞星火
os.environ["IFLYTEK_SPARK_APP_ID"] = "5af89b1c"
os.environ["IFLYTEK_SPARK_API_KEY"] = "a21950a0e2f8d21eeaf0cf136ea34417"
os.environ["IFLYTEK_SPARK_API_SECRET"] = "ZGQ1NjMzMDQxZWMzYmIyNDRkZmI5MGYy"
from langchain_community.llms import SparkLLM
# Load the model
spark_llm = SparkLLM()

os.environ["BING_SUBSCRIPTION_KEY"] = '362c8a355c884169b930183a7b481b83'
os.environ["BING_SEARCH_URL"] = "https://api.bing.microsoft.com/v7.0/search"

from langchain_community.utilities import BingSearchAPIWrapper
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain_community.tools.bing_search import BingSearchResults

search_wrapper = BingSearchAPIWrapper(k=4)

# 测试bing搜索api
# result = search_wrapper.run("python")
# print(result)

from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain.agents.tools import Tool
from langchain.chains.llm_math.base import LLMMathChain

# llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)

tools = [
    Tool(
        name = "Search",
        func=search_wrapper.run,
        description="useful for when you need to answer questions about current events"
    ),
    # Tool(
    #     name="Calculator",
    #     func=llm_math_chain.run,
    #     description="useful for when you need to answer questions about math"
    # ),
]


planner = load_chat_planner(llm)
executor = load_agent_executor(llm_1, tools, verbose=True)
agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)

agent.invoke("截至2024年7月6日，2024年欧洲杯西班牙队有没有出局?请使用中文回答")
