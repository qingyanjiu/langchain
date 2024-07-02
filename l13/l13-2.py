'''
PlayWrightBrowserToolkit 为 PlayWright 浏览器提供了一系列交互的工具，可以在同步或异步模式下操作
'''

from langchain.agents.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser

async_browser = create_async_playwright_browser()
toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
tools = toolkit.get_tools()
print(tools)

from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatAnthropic, ChatOpenAI

# LLM不稳定，对于这个任务，可能要多跑几次才能得到正确结果
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.5)

agent_chain = initialize_agent(
    tools,
    llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)

async def main():
    response = await agent_chain.ainvoke("https://www.bilibili.com网站的header是什么")
    print(response)

import asyncio
loop = asyncio.get_event_loop()
loop.run_until_complete(main())