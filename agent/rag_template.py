# agentic_workflow_langchain_decorator.py
"""
LangChain + @tool 版增强 Agent 工作流
功能：
- Planner -> Executor -> Evaluator -> Answer Composer
- 使用 @tool 装饰器注册工具
- Executor 支持 RAG 流水线（RetrievalQA）
- 多轮 Memory 管理
- 持久化：JSON / SQLite
"""

import json, time, uuid, os
from typing import List
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, initialize_agent, AgentType
from langgraph.prebuilt import create_react_agent
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
import requests
import logging

logging.basicConfig(
    filename='app.log',       # 写入文件
    filemode='a',             # 追加模式，可改为 'w' 覆盖
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

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

# -------------------------------
# 持久化
# -------------------------------
class Persistor:
    def __init__(self, method: str = "json", path: str = "agent_state.json", sqlite_path: str = "agent_state.db"):
        self.method = method.lower()
        self.path = path
        self.sqlite_path = sqlite_path

    def save(self, key: str, data: dict):
        if not data:
            return
        if self.method=="json":
            with open(self.path,"w",encoding="utf-8") as f:
                json.dump({key:_safe_serialize(data)}, f, ensure_ascii=False, indent=2)
        elif self.method=="sqlite":
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS agent_state (key TEXT PRIMARY KEY, payload TEXT, updated_at REAL)")
            c.execute("REPLACE INTO agent_state (key,payload,updated_at) VALUES (?,?,?)", (key,json.dumps(data,ensure_ascii=False),time.time()))
            conn.commit()
            conn.close()

    def load(self, key: str):
        if self.method=="json":
            if not os.path.exists(self.path): return None
            with open(self.path,"r",encoding="utf-8") as f:
                try:
                    d = json.load(f)
                except json.JSONDecodeError:
                    d = None
            return d.get(key) if d else None
        elif self.method=="sqlite":
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            c = conn.cursor()
            c.execute("SELECT payload FROM agent_state WHERE key=?", (key,))
            row = c.fetchone()
            conn.close()
            return json.loads(row[0]) if row else None

# -------------------------------
# 工具
# -------------------------------

# ======== 定义知识库控制器 ========
class DifyKnowledgeBaseController:
    def __init__(self, base_url: str, api_key: str, dataset_id: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.dataset_id = dataset_id

    def search(self, query: str):
        """调用 Dify 检索接口"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/retrieve"
        resp = requests.post(url, headers=self.headers, json={"query": query})
        resp.raise_for_status()
        return resp.json().get("records", [])

    def list_files(self, page: int = 1, page_size: int = 100):
        """列出知识库文件"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents?page={page}&limit={page_size}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def list_datasets(self, page: int = 1, page_size: int = 100):
        """获取知识库列表信息"""
        url = f"{self.base_url}/v1/datasets?page={page}&limit={page_size}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def read_file_chunks(self, doc_id: str):
        """读取文件的分段内容"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents/{doc_id}/segments"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("data", [])

# ======== 初始化知识库控制器 ========
kb_controller = DifyKnowledgeBaseController(
    base_url="http://localhost",
    api_key="dataset-XqsUQ5VQWkejtgJHFzEsZLar",
    dataset_id="c5153abf-19b3-429b-9902-812dd85c8bfc"
)

@tool("query_knowledge_base")
def query_knowledge_base(query: str) -> str:
    """根据问题在知识库中进行语义检索，返回候选片段列表"""
    results = kb_controller.search(query)
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool("list_datasets")
def list_datasets() -> str:
    """获取知识库列表"""
    results = kb_controller.list_datasets()
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool("read_file_chunks")
def read_file_chunks(doc_ids: List[str]) -> str:
    """读取指定文件的所有分段内容"""
    if not doc_ids:
        return "请提供文件ID数组"
    results = {}
    for doc_id in doc_ids:
        results[doc_id] = kb_controller.read_file_chunks(doc_id)
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool("list_files")
def list_files(page: int = 1, page_size: int = 10) -> str:
    """列出当前知识库中的文件，返回文件ID、文件名和chunk数"""
    results = kb_controller.list_files(page, page_size)
    return json.dumps(results, ensure_ascii=False, indent=2)

# =========== API查询工具 ==========

# api工具专用的llm
api_llm = ChatOpenAI(
    api_key="123",
    temperature=0,
    max_retries=3,
    base_url="http://localhost:1234/v1",
    model="qwen/qwen3-8b"
)

class QueryParams(BaseModel):
    area: str = Field(..., description="区域名称，比如‘东区’或‘A栋’")
    start_date: str = Field(..., description="开始日期，格式为YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期，格式为YYYY-MM-DD")
    groupby: str = Field(..., description="分组维度，例如按照楼层、公司、部门等分组")
    
# API查询工具内部调用 llm
def call_model_in_tool(system_prompt: str, user_prompt: str):
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    # 在 tool 内部直接调用 llm
    response = api_llm.invoke(messages)
    return response

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


# -------------------------------
# Workflow Engine
# -------------------------------
class LCWorkflowEngine:
    def __init__(self, run_id, llm, tools, persistor: Persistor, system_prompt, max_iters=3):
        self.llm = llm
        self.persistor = persistor
        self.max_iters = max_iters
        self.run_id = str(uuid.uuid4()) if not run_id else run_id
        self.trace = []
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        self.tools = tools
        self.system_prompt = system_prompt
        agent = create_react_agent(self.llm, tools=self.tools, prompt=self.system_prompt)
        self.agent = AgentExecutor(agent=agent, tools=self.tools, memory=self.memory, verbose=True)


    # 从持久化的trace中恢复对话历史
    def _restore_memory(self):
        # 遍历 trace，把历史对话按顺序添加到 memory（只找最近5条）
        for entry in self.trace[-5:]:
            if entry['phase'] == 'executor_agent':
                # entry['output'] 可以是 AIMessage 或字符串
                out = entry['output']
                if isinstance(out, AIMessage):
                    # agent 回答
                    self.memory.chat_memory.add_ai_message(out.content)
                elif isinstance(out, str):
                    # 字符串也可以直接加入
                    self.memory.chat_memory.add_ai_message(out)
            elif entry['phase'] == 'loop_start':
                # loop_start 的 input 就是用户提问
                step_list = entry['meta'].get("plan", [])
                for step in step_list:
                    self.memory.chat_memory.add_user_message(step)
    def _trace(self, phase, meta, output):
        self.trace.append({"ts":time.time(),"phase":phase,"meta":meta,"output":output})
        
    def do_plan(self, user_query: str):
        plan_prompt = f"""
        请生成一个执行计划，该计划将按照以下步骤执行：
        {user_query}
        执行计划需要满足以下条件：
        - 步骤数量不能超过10个
        - 步骤不能重复
        - 步骤不能依赖其他步骤的结果
        """

    def run(self, user_query: str):
        key = f"run:{self.run_id}"
        saved = self.persistor.load(key)
        if saved:
            self.trace = saved.get("trace", [])
    
        iter_count = 0
        aggregated = []
        
        # TODO 如果是多个请求，则先生成plan，再将plan交给engine去执
        plan = [user_query]

        while iter_count < self.max_iters:
            iter_count += 1
            # 恢复之前持久化的对话历史
            self._restore_memory()
            self._trace("loop_start", {"iter": iter_count, "plan": plan}, "")
            for step in plan:
                # 通过 Agent普通工具调用
                try:
                    out = self.agent.invoke({"input": step})
                    aggregated.append({"step":step,"output":_safe_serialize(out)})
                    self._trace("executor_agent", {"step":step}, out)
                except Exception as e:
                    aggregated.append({"step":step,"output":str(e)})

            # Evaluator
            eval_prompt = f"""
            你是 Evaluator，判断以下内容是否充分回答用户问题：
            用户问题：{user_query}
            聚合结果：
            {json.dumps(aggregated, ensure_ascii=False)}
            若充分请返回 OK，否则给出下一步明确要执行的动作。
            """
            eval_resp = self.llm.invoke(eval_prompt)
            decision_text = eval_resp.content
            self._trace("evaluator", {"aggregated_count":len(aggregated)}, decision_text)

            if "ok" in decision_text.lower() or "充分" in decision_text.lower():
                answer_prompt = f"""
                你是 Answer Composer，请基于聚合结果生成回答：
                用户问题：{user_query}
                聚合结果：
                {json.dumps(aggregated, ensure_ascii=False)}
                输出自然语言答案并列出引用来源。
                """
                final_answer = self.llm.invoke(answer_prompt)
                self._trace("compose_answer", {}, final_answer)
                self.persist()
                return {"status":"ok","answer":final_answer,"trace":self.trace}
            else:
                plan = [decision_text.splitlines()[0]]
                self._trace("plan_updated", {"new_plan":plan}, decision_text)

        self._trace("max_iters_exceeded", {}, "")
        self.persist()
        return {"status":"insufficient","message":"多轮仍无法得到足够证据","trace":self.trace}

    def persist(self):
        key = f"run:{self.run_id}"
        payload = {"trace":self.trace}
        self.persistor.save(key, payload)

# -------------------------------
# Demo
# -------------------------------
def demo():
    
    llm = ChatOpenAI(
        api_key="123",
        temperature=0,
        max_retries=3,
        base_url="http://localhost:1234/v1",
        model="qwen/qwen3-8b"
    )

    api_tools_name = [
        '能耗数据统计', '运营数据统计', '安防数据统计'
    ]
    
    datasets_tools_name = [
        'query_knowledge_base', 'read_file_chunks', 'list_datasets', 'list_files'
    ]

    # 直接使用 @tool 装饰器的函数
    tools = [query_knowledge_base, read_file_chunks, list_datasets, list_files, 能耗数据统计, 运营数据统计, 安防数据统计]
    
    # persistor = Persistor(method="sqlite", sqlite_path="agent_state.db")
    persistor = Persistor()

    engine = LCWorkflowEngine(llm=llm, tools=tools, persistor=persistor, run_id="d08cb46d-71ea-4459-b7cb-5f8187ab8cf1",
                            system_prompt=
    f"""你是一个 Agentic RAG 助手,请根据要求依次通过知识库检索以及API查询来回答问题。
    
    * 在检索知识库的时候，请使用以下几个工具来进行检索:{','.join(datasets_tools_name)}
    遵循以下步骤：
    1. 用 query_knowledge_base 搜索知识库中相关内容，获得候选文件和片段线索
    2. 使用 read_file_chunks 精读最相关的2-3个片段内容作为证据
    3. 基于读取的具体片段内容组织答案
    4. 回答末尾用"引用："格式列出实际读取的fileId和chunkIndex
    5. 回答末尾用"调用："格式列出实际调用的tool和参数

    重要规则：
    - 如果检索知识库的结果为空，例如 
    query_knowledge_base 返回为空数组 [] 或读取的文件片段内容为空，请不要继续调用其他工具，也不要根据自己的理解生成答案；
    请直接回答："知识库中缺少相关信息，建议补充相关文档。"
    - 你的所有回答都必须基于实际读取到的片段。
    - 若找不到足够的证据，就明确说明“知识库中暂缺相关信息”。
    - 优先选择评分高的搜索结果进行深入阅读。
    - 如果实在找不到答案，就回答你不知道。
    
    * 在使用API查询的时候，请使用以下几个工具来进行检索:{','.join(api_tools_name)}。你的任务是:
    - 根据要求组合查询条件，并从工具中选择合适的工具进行查询
    - 将工具查询结果数据通过专业的语言转达给用户
    对于查询条件数据中的字段，说明如下：
    - area: 如果是整个园区，则值为'park';如果是楼层，则值为'B1F','1F','2F'等;
    - start_date: 查询开始时间，格式为YYYY-MM-DD
    - end_date: 查询结束时间，格式为YYYY-MM-DD
    - groupby: 如果是按区域统计，则为'area', 如果按公司统计，则为'company', 如果按时间统计，则为'time'
    - 如果没有满足条件的API，可以放弃API查询环节，直接使用知识库检索的结果来回答问题。
    
    如果仍然无法得到足够的证据，请直接回答："未检索到任何相关信息，建议补充相关文档及数据接口。"
    """)
    
    q = "请概述 RAG 的优缺点，并给出引用。"
    
    res = engine.run(q)
    print(res['answer'])

if __name__=="__main__":
    demo()