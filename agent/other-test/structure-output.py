from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState


class WeatherResponse(BaseModel):
    """Respond to the user with this"""

    temperature: float = Field(description="The temperature in fahrenheit")
    wind_directon: str = Field(
        description="The direction of the wind in abbreviated form"
    )
    wind_speed: float = Field(description="The speed of the wind in km/h")


# Inherit 'messages' key from MessagesState, which is a list of chat messages
class AgentState(MessagesState):
    # Final structured response from the agent
    final_response: WeatherResponse


@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It is cloudy in NYC, with 5 mph winds in the North-East direction and a temperature of 70 degrees"
    elif city == "sf":
        return "It is 75 degrees and sunny in SF, with 3 mph winds in the South-East direction"
    else:
        raise AssertionError("Unknown city")


tools = [get_weather]

llm = ChatOpenAI(
    temperature=0,
    max_retries=3,
    api_key="123",
    base_url="http://localhost:1234/v1/",
    model="google/gemma-3-12b"
)

model_with_tools = llm.bind_tools(tools)
model_with_structured_output = llm.with_structured_output(WeatherResponse)


from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage


# Define the function that calls the model
def call_model(state: AgentState):
    response = model_with_tools.invoke(state["messages"])
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
    
    

from langchain_core.messages import HumanMessage

state = {
    "messages": [HumanMessage(content="今天纽约的天气怎么样？")]
}

result = graph.invoke(state)
print(result)
