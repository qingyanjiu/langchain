# uvicorn app:app --host 0.0.0.0 --port 8000 --reload

import json
from fastapi import FastAPI, WebSocket
from memory.store import MemoryStore
from agent.executor import AgentExecutorWrapper
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from models.llm import create_llm
from tools.rag_tools import TOOLS as RAG_TOOLS
from agent.rag_prompts import SYSTEM_PROMPT
import logging

logging.basicConfig(
    filename='app.log',
    # 追加模式 'a'，覆盖模式 'w' 
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

app = FastAPI()
memory_store = MemoryStore()

def _safe_serialize(obj):
    """递归将 BaseMessage 转为 dict"""
    if isinstance(obj, BaseMessage):
        return obj.model_dump()
    elif isinstance(obj, list):
        return [_safe_serialize(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    else:
        return obj

MODEL_URL = 'https://api.siliconflow.cn/v1'
MODEL_NAME = 'Qwen/Qwen3-Next-80B-A3B-Instruct'

# MODEL_URL = "http://192.168.100.85:1234/v1"
# MODEL_NAME = "qwen/qwen3-vl-8b"

# 全局模型和工具
llm = create_llm(
    base_url=MODEL_URL,
    model=MODEL_NAME
)

@app.websocket("/agentic_rag_query/{user_id}")
async def agent_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()

    # 为当前用户创建独立的 AgentExecutor
    rag_executor = AgentExecutorWrapper(
        llm=llm,
        tools=RAG_TOOLS,
        memory_store=memory_store,
        user_id=user_id,
        system_prompt=SYSTEM_PROMPT
    )

    while True:
        try:
            data = await websocket.receive_text()
            query = json.loads(data).get("query")
            if not query:
                await websocket.send_text(json.dumps({"error": "empty query"}))
                continue

            # 假设 agent 是通过 create_agent 创建的，并且支持 astream
            async for chunk in rag_executor.stream_run(query):
                text = _safe_serialize(chunk)
                # 如果是最后结束的消息，直接拿message
                if(text['event'] == 'on_chain_end'
                    and 'output' in text['data'] 
                    and text['name'] == 'executor_agent'):
                    # 取最后 messagetext['name'] == 'executor_agent'):
                    output_json = {
                        "event": "final_answer", 
                        "data": text['data']['output']['messages'][-1]['content']
                    }
                await websocket.send_text(json.dumps(text))
                
            await websocket.send_text(json.dumps({"status": "done", "data": output_json}))
            
            logging.info(f"query done -- {user_id}")

        except Exception as e:
            await websocket.send_text(json.dumps({"error": str(e)}))
