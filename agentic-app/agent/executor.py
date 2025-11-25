from langchain_classic.agents import AgentExecutor
from langchain.agents import create_agent

from memory.store import MemoryStore

class AgentExecutorWrapper:
    def __init__(self, llm, tools, memory_store: MemoryStore, user_id, system_prompt=None, agent_recursion_limit=10):
        self.llm = llm
        self.tools = tools
        self.user_id = user_id
        self.memory_store = memory_store
        self.memory = memory_store.get_memory(user_id)
        self.agent_recursion_limit = agent_recursion_limit

        self.agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt, debug=False, name="executor_agent")
        self.executor = create_agent(model=llm, tools=tools, system_prompt=system_prompt, debug=False, name="executor_agent")
        # self.executor = AgentExecutor(agent=self.agent, tools=tools, memory=self.memory, verbose=True)

    def run(self, query: str):
        # 同步调用
        output = self.executor.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config={
                "recursion_limit": self.agent_recursion_limit
            }
        )
        self.memory_store.append_trace(self.user_id, "executor_agent", {"query": query}, str(output))
        return output

    async def stream_run(self, query: str, version="v2"):
        """
        异步流式调用 agent，基于 astream_events
        """
        inputs = {"messages": [{"role": "user", "content": query}]}
        # 用 astream_events 监听事件流
        async for event in self.executor.astream_events(
            inputs, 
            version=version,
            config={
                "recursion_limit": self.agent_recursion_limit
            }):
            # event 是一个 dict，包含 event["event"]，event["data"] 等
            # 可以根据事件类型过滤，只输出 token 或最终答案
            yield event

        # 流结束后，你可以根据需要再触发一次 run 完成（可选）
        # final = self.executor.run(query)
        # yield {"event": "final", "output": final}