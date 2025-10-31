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

@tool(args_schema=QueryParams, description='''
    用于查询园区能耗相关数据。
    可根据指定的区域、时间范围和分组方式返回能耗统计结果。
    常用于生成能耗分析报告或趋势分析。
    ''')
def 能耗数据统计(area: str, start_date: str, end_date: str, groupby: str):
    """统计园区内的能耗数据"""
    system_prompt = '''
    你是一位能耗分析专家，请根据输入数据生成专业的能耗分析报告。
    请用简洁、客观的语气说明能耗趋势和异常点。
    *** 注意：***
    - 你需要将工具返回的数据通过对应的专业知识提取出来，生成报告的文本
    - 不要编造数据，如果无法通过工具的查询结果总结出专业的内容，就直接回答"没有找到相关数据"。
    '''
    # 拼接用户输入内容
    user_prompt = f"""
    园区：{area}
    时间段：{start_date} 至 {end_date}
    统计维度：{groupby}
    请生成分析报告。
    """
    response = call_model_in_tool(system_prompt, user_prompt)
    return response.content


@tool(args_schema=QueryParams, description='''
    用于查询园区运营相关数据。
    可根据指定的区域、时间范围和分组方式返回运营统计结果。
    常用于生成运营分析报告或趋势分析。
    ''')
def 运营数据统计(area: str, start_date: str, end_date: str, groupby: str):
    """统计园区内的运营数据"""
    system_prompt = '''
    你是一位运营分析专家，请根据输入数据生成专业的运营分析报告。
    请用简洁、客观的语气说明运营趋势和异常点。
    *** 注意：***
    - 你需要将工具返回的数据通过对应的专业知识提取出来，生成报告的文本
    - 不要编造数据，如果无法通过工具的查询结果总结出专业的内容，就直接回答"没有找到相关数据"。
    '''
    # 拼接用户输入内容
    user_prompt = f"""
    园区：{area}
    时间段：{start_date} 至 {end_date}
    统计维度：{groupby}
    请生成分析报告。
    """
    response = call_model_in_tool(system_prompt, user_prompt)
    return response.content


@tool(args_schema=QueryParams, description='''
    用于查询园区安防相关数据。
    可根据指定的区域、时间范围和分组方式返回安防统计结果。
    常用于生成安防分析报告或趋势分析。
    ''')
def 安防数据统计(area: str, start_date: str, end_date: str, groupby: str):
    """统计园区内的安防数据"""
    system_prompt = '''
    你是一位安防分析专家，请根据输入数据生成专业的安防分析报告。
    请用简洁、客观的语气说明安防趋势和异常点。
    *** 注意：***
    - 你需要将工具返回的数据通过对应的专业知识提取出来，生成报告的文本
    - 不要编造数据，如果无法通过工具的查询结果总结出专业的内容，就直接回答"没有找到相关数据"。
    '''
    # 拼接用户输入内容
    user_prompt = f"""
    园区：{area}
    时间段：{start_date} 至 {end_date}
    统计维度：{groupby}
    请生成分析报告。
    """
    response = call_model_in_tool(system_prompt, user_prompt)
    return response.content


tools = [能耗数据统计, 运营数据统计, 安防数据统计]

llm = ChatOpenAI(
    temperature=0,
    max_retries=3,
    base_url="http://localhost:1234/v1",
    model="qwen/qwen3-8b"
)

model_with_tools = llm.bind_tools(tools)
# 返回值对象格式化，就定义对应的class传入TYPE
# model_with_structured_output = llm.with_structured_output(TYPE)
model_with_structured_output = model_with_tools


from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage




# 工具内部调用 llm
def call_model_in_tool(system_prompt: str, user_prompt: str):
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    # 在 tool 内部直接调用 llm
    response = llm.invoke(messages)
    return response


# 调用llm选择工具（agent）
def call_model(state: AgentState):
    system_msg = SystemMessage(content='''
    你是园区数据分析助手，你的任务是:
    - 根据要求组合查询条件，并从工具中选择合适的工具进行查询
    - 将工具查询结果数据通过专业的语言转达给用户
    对于查询条件数据中的字段，说明如下：
    - area: 如果是整个园区，则值为'park';如果是楼层，则值为'B1F','1F','2F'等;
    - start_date: 查询开始时间，格式为YYYY-MM-DD
    - end_date: 查询结束时间，格式为YYYY-MM-DD
    - groupby: 如果是按区域统计，则为'area', 如果按公司统计，则为'company', 如果按时间统计，则为'time'
    ''')
    response = model_with_tools.invoke([system_msg] + state["messages"])
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


# 显示流程图
def show_flow_graph():
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
        

# 将结果转为指定对象格式
def respond(state: AgentState):
    # We call the model with structured output in order to return the same format to the user every time
    # state['messages'][-2] is the last ToolMessage in the convo, which we convert to a HumanMessage for the model to use
    # We could also pass the entire chat history, but this saves tokens since all we care to structure is the output of the tool
    # response = model_with_structured_output.invoke(
    #     [HumanMessage(content=state["messages"][-2].content)]
    # )
    
    response = state["messages"][-1].content
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
    
show_flow_graph()

state = {
    "messages": [HumanMessage(content="按公司统计近一年整个园区的安防数据")]
}

result = graph.invoke(state)
print(result)
