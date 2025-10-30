from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage


# 返回值类型
class AgentState(MessagesState):
    # Final structured response from the agent
    final_response: map

class QueryParams(BaseModel):
    area: str = Field(..., description="区域名称，比如‘东区’或‘A栋’")
    start_date: str = Field(..., description="开始日期，格式为YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期，格式为YYYY-MM-DD")
    groupby: str = Field(..., description="分组维度，例如按照楼层、公司、部门等分组")

@tool
def 能耗数据统计(params: QueryParams):
    """Use this to get weather information."""
    return f'能耗数据查询-{params}'

@tool
def 运营数据统计(params: QueryParams):
    """Use this to get weather information."""
    return f'运营数据统计-{params}'

@tool
def 安防数据统计(params: QueryParams):
    """Use this to get weather information."""
    return f'安防数据统计-{params}'



tools = [能耗数据统计, 运营数据统计, 安防数据统计]

llm = ChatOpenAI(
    temperature=0,
    max_retries=3,
    api_key="123",
    base_url="http://localhost:1234/v1/",
    model="google/gemma-3-12b"
)

model_with_tools = llm.bind_tools(tools)
# 返回值对象格式化，就定义对应的class传入TYPE
# model_with_structured_output = llm.with_structured_output(TYPE)
model_with_structured_output = model_with_tools


from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage


# Define the function that calls the model
def call_model(state: AgentState):
    system_msg = SystemMessage(content='''
    你是园区数据分析助手，请根据要求组合查询条件，并从工具中选择合适的工具进行查询。
    对于查询条件数据中的字段，说明如下：
    - area: 如果是整个园区，则值为'park';如果是楼层，则值为'B1F','1F','2F'等;
    - start_date: 查询开始时间，格式为YYYY-MM-DD
    - end_date: 查询结束时间，格式为YYYY-MM-DD
    - groupby: 如果是按区域统计，则为'area', 如果按公司统计，则为'company', 如果按时间统计，则为'time'
    ''')
    response = model_with_tools.invoke([system_msg] + state["messages"])
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


# Define the function that responds to the user
def respond(state: AgentState):
    # We call the model with structured output in order to return the same format to the user every time
    # state['messages'][-2] is the last ToolMessage in the convo, which we convert to a HumanMessage for the model to use
    # We could also pass the entire chat history, but this saves tokens since all we care to structure is the output of the tool
    response = model_with_structured_output.invoke(
        [HumanMessage(content=state["messages"][-2].content)]
    )
    # We return the final answer
    return {"final_response": response}


# Define the function that determines whether to continue or not
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we respond to the user
    if not last_message.tool_calls:
        return "respond"
    # Otherwise if there is, we continue
    else:
        return "continue"


# Define a new graph
workflow = StateGraph(AgentState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("respond", respond)
workflow.add_node("tools", ToolNode(tools))

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "respond": "respond",
    },
)

workflow.add_edge("tools", "agent")
workflow.add_edge("respond", END)
graph = workflow.compile()

# 生成 Mermaid PNG 并保存
graph_png = graph.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(graph_png)

# 在系统默认查看器打开
import os
import platform

if platform.system() == "Darwin":  # macOS
    os.system("open workflow.png")
elif platform.system() == "Windows":
    os.startfile("workflow.png")
else:  # Linux
    os.system("xdg-open workflow.png")
    

state = {
    "messages": [HumanMessage(content="按公司统计近一年整个园区的安防数据")]
}

result = graph.invoke(state)
print(result)
