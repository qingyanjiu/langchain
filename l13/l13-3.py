'''
Self-Ask with Search 也是 LangChain 中的一个有用的代理类型（SELF_ASK_WITH_SEARCH）。
它利用一种叫做 “Follow-up Question（追问）”加“Intermediate Answer（中间答案）”的技巧，来辅助大模型寻找事实性问题的过渡性答案，从而引出最终答案

以下代码没效果，这个东西有bug。官网有issue，或许不同的llm表现不同
'''

# 初始化大语言模型
import os
from langchain_community.llms.ollama import Ollama
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0)

# 讯飞星火
# os.environ["IFLYTEK_SPARK_APP_ID"] = "5af89b1c"
# os.environ["IFLYTEK_SPARK_API_KEY"] = "a21950a0e2f8d21eeaf0cf136ea34417"
# os.environ["IFLYTEK_SPARK_API_SECRET"] = "ZGQ1NjMzMDQxZWMzYmIyNDRkZmI5MGYy"
# from langchain_community.llms import SparkLLM
# # Load the model
# llm = SparkLLM()

os.environ["BING_SUBSCRIPTION_KEY"] = '362c8a355c884169b930183a7b481b83'
os.environ["BING_SEARCH_URL"] = "https://api.bing.microsoft.com/v7.0/search"

from langchain_community.utilities import BingSearchAPIWrapper
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain_community.tools.bing_search import BingSearchResults

search_wrapper = BingSearchAPIWrapper()
# search = BingSearchResults(api_wrapper=search_wrapper, name="Intermediate Answer")
# tools = [search]

# 测试bing搜索api
# result = search_wrapper.run("python")
# print(result)

tools = [ Tool( name="Intermediate Answer", func=search_wrapper.run, description="useful for when you need to ask with search", )]
# 这样写是不行的
self_ask_with_search = initialize_agent( 
                                        tools, 
                                        llm, 
                                        agent=AgentType.SELF_ASK_WITH_SEARCH, 
                                        verbose=True)
self_ask_with_search.invoke( "昨天2024年欧洲杯决赛圈被淘汰的球队是哪几支？请使用中文回答" )
