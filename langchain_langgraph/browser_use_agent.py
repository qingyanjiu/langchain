import asyncio
import os
from browser_use import BrowserSession, BrowserProfile, Agent
from langchain_openai import ChatOpenAI

'''
pip install browser_use==0.2.4 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install langchain_openai -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install
'''

OPENAI_API_KEY = 'sk-sdcxstsuwiefzutgkridojrlcovgaggxddyvaicqwynpxebq'
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
llm = ChatOpenAI(model='Qwen/Qwen2.5-32B-Instruct',
            api_key=OPENAI_API_KEY,
            base_url='https://api.siliconflow.cn/v1',
            streaming=True,
            temperature=0,
            request_timeout=120,
            max_retries=0
            )

browser_profile = BrowserProfile(
    headless=False,
    # cookies_file="path/to/cookies.json",
    wait_for_network_idle_page_load_time=3.0,
    viewport={"width": 1280, "height": 1100},
    # locale='en-US',
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
    highlight_elements=True,
    viewport_expansion=500,
    # allowed_domains=['*.google.com', 'http*://*.wikipedia.org'],
)

browser_session = BrowserSession(
    browser_profile=browser_profile,
)

async def main():
    # you can drive a session without the agent / reuse it between agents
    await browser_session.start()
    page = await browser_session.get_current_page()
    await page.goto('https://www.baidu.com')


    agent = Agent(
        task='请打开bilibili首页，在搜索框中输入“Python编程”，按回车键进行搜索',
        llm=llm,
        use_vision=False,
        page=page,                        # optional: pass a specific playwright page to start on
        browser_session=browser_session,  # optional: pass an existing browser session to an agent
    )
    
    result = await agent.run()
    print(result)
    await browser_session.close()

asyncio.run(main())