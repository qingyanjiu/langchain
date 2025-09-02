from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.callbacks.base import BaseCallbackHandler

# 1. 自定义 CallbackHandler 处理流式 token 输出
class StreamCallbackHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(token, end="", flush=True)  # 实时输出 token
        
OPENAI_API_KEY = 'hxkj2025'
llm = ChatOpenAI(model='deepseek',
            api_key=OPENAI_API_KEY,
            base_url='https://ai01.hpccube.com:65016/ai-forward/d90177765e5346e891bf019a18a16f3da0009000/v1',
            # base_url='https://ai111.hpccube.com:65062/ai-forward/83d4e0a0eee742e5a182cd43cae9dab9a0008000/v1',
            streaming=True,
            temperature=0,
            request_timeout=120,
            max_retries=0,
            callbacks=[StreamCallbackHandler()]  # 注册回调
)

# OPENAI_API_KEY = 'sk-sdcxstsuwiefzutgkridojrlcovgaggxddyvaicqwynpxebq'
# llm = ChatOpenAI(model='Qwen/Qwen2.5-32B-Instruct',
#             api_key=OPENAI_API_KEY,
#             base_url='https://api.siliconflow.cn/v1',
#             streaming=True,
#             temperature=0,
#             request_timeout=120,
#             max_retries=0,
#             callbacks=[StreamCallbackHandler()]
#             )


# 2. 定义工具函数（工具可以是任何函数）
@tool
def calculator_tool(expression: str) -> str:
    """Evaluates simple mathematical expressions."""
    exp = expression.split('\n')[0]
    end = expression.split('\n')[1]
    try:
        return f'str(eval(exp))\n{end}'
    except Exception as e:
        return f"Error: {str(e)}"

# 3. 创建工具列表
tools = [
    Tool.from_function(
        func=calculator_tool,
        name="Calculator",
        description="Useful for solving basic math problems with python language."
    )
]

# 4. 初始化 ReAct Agent
agent_executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # 使用 ReAct agent 类型
    handle_parsing_errors=True,
    max_iterations=2,
    verbose=True
)

# 5. 运行 agent
response = agent_executor.run("101111212309123123的立方根是什么？请回答中文")
