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

from dify_datasets_controller import DifyKnowledgeBaseController
import json, time, uuid, os
from typing import List
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_classic.agents import AgentExecutor
from langchain_core.tools import tool
from langchain_classic.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain_core.prompts.chat import PromptTemplate
import logging

# MODEL_URL = 'https://api.siliconflow.cn/v1'
# MODEL_NAME = 'Qwen/Qwen3-Next-80B-A3B-Instruct'

MODEL_URL = 'http://192.168.100.85:1234/v1'
MODEL_NAME = 'qwen/qwen3-vl-8b'

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

# ======== 初始化知识库控制器 ========
# kb_controller = DifyKnowledgeBaseController(
#     base_url="http://localhost",
#     dataset_id="f61a2250-27bd-4e6f-8815-6820c21d5dc1"
# )
kb_controller = DifyKnowledgeBaseController(
    base_url="http://192.168.100.85",
    dataset_id="2c2b721d-365b-4ad6-ac7d-c3cdd601c742"
)

class QueryKBParams(BaseModel):
    query: str
@tool(args_schema=QueryKBParams, description="根据问题在知识库中进行语义检索，返回候选片段列表。参数是一个由数字、字母、-组成的字符串，不包含任何其他字符。")
def query_knowledge_base(query: str) -> str:
    """根据问题在知识库中进行语义检索，返回候选片段列表"""
    try:
        results = kb_controller.search(query)
        # 包含文本过短的，过滤掉
        results = [r for r in results if len(r['segment']['content']) > 10]
        logging.info(f"query_knowledge_base检索知识库结果：{results}")
    except Exception as e:
        logging.error(f"Error querying knowledge base: {e}")
        return "查询知识库时出错，请稍后再试"
    return json.dumps(results, ensure_ascii=False, indent=2)

@tool(description="获取知识库列表")
def list_datasets() -> str:
    """获取知识库列表"""
    try:
        results = kb_controller.list_datasets()
    except Exception as e:
        logging.error(f"Error listing datasets: {e}")
        return "获取知识库列表时出错，请稍后再试"
    return json.dumps(results, ensure_ascii=False, indent=2)

class ReadFileChunksParams(BaseModel):
    doc_id: str
    chunk_start: int
    chunk_end: int
@tool(args_schema=ReadFileChunksParams, description='''
    读取指定文件的所有分段内容，作用是从文档中检索复数个分段的内容。
    doc_id为文档ID；
    chunk_start为要检索的文档的开始分段编号，
    chunk_end为要检索的文档的结束分段编号
    ''')
def read_file_chunks(doc_id: str, chunk_start: int, chunk_end: int) -> str:
    """读取指定文件的所有分段内容"""
    if not doc_id:
        return "请提供文档ID"
    results = {"messages": [{"role": "system", "content": ""}]}
    try:
        for chunk_no in range(chunk_start, chunk_end + 1):
            chunk_data = kb_controller.read_file_chunks(doc_id, page=chunk_no)
            chunk_content = chunk_data[0]['content']
            results["messages"][0]['content'] += f'{chunk_content}\n'
        logging.info(f'read_file_chunks：{results["messages"][0]["content"][:100]}...')
    except Exception as e:
        logging.error(f"Error reading file chunks: {e}")
        return "读取文件分段内容时出错，请稍后再试"
    return json.dumps(results, ensure_ascii=False, indent=2)


class ListFilesParams(BaseModel):
    page: int = 1
    page_size: int = 10

@tool(args_schema=ListFilesParams, description="列出当前知识库中的文件，返回文件ID、文件名和chunk数")
def list_files(page: int = 1, page_size: int = 10) -> str:
    """列出当前知识库中的文件，返回文件ID、文件名和chunk数"""
    try:
        results = kb_controller.list_files(page, page_size)
    except Exception as e:
        logging.error(f"Error listing files: {e}")
        return "列出文件时出错，请稍后再试"
    return json.dumps(results, ensure_ascii=False, indent=2)

# =========== API查询工具 ==========

# api工具专用的llm
api_llm = ChatOpenAI(
    # api_key="123",
    temperature=0,
    max_retries=3,
    base_url=f"{MODEL_URL}",
    model=f"{MODEL_NAME}"
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
    def __init__(self, run_id, llm, tools, persistor: Persistor, system_prompt, max_iters=2, agent_recursion_limit = 10):
        # agent 递归调用限制
        self.agent_recursion_limit = agent_recursion_limit
        self.llm = llm
        self.persistor = persistor
        # 流程迭代次数
        self.max_iters = max_iters
        self.run_id = str(uuid.uuid4()) if not run_id else run_id
        self.trace = []
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        self.tools = tools
        self.system_prompt = system_prompt
        self.agent = create_agent(model=self.llm, tools=self.tools, system_prompt=self.system_prompt, debug = False)

    # 从持久化的trace中恢复对话历史11\5////////////1                                                                    \
        # \\\\\\\\\\\\\\\trace，把历史对话按顺序添加到 memory（只找最近5条）
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
        
    # 兼容deepseek,删除think
    def remove_think(self, content):
        ret = content
        if(len(content.split('</think>')) > 1):
            ret = content.split('</think>')[1]
            ret = content.replace('\n', '')
        return ret
        
    def do_plan(self, user_query: str):
        plan_prompt = f"""
        请生成一个执行计划，该计划将按照以下步骤执行：
        {user_query}
        执行计划需要满足以下条件：
        - 步骤数量不能超过10个
        - 步骤不能重复
        - 步骤不能依赖其他步骤的结果
        """

    def run(self, user_query: object):
        
        key = f"run:{self.run_id}"
        saved = self.persistor.load(key)
        if saved:
            self.trace = saved.get("trace", [])
    
        iter_count = 0
        aggregated = []
        
        # TODO 如果是多个请求，则先生成plan，再将plan交给engine去执
        plan = [user_query['prompt']]

        while iter_count < self.max_iters:
            iter_count += 1
            # 恢复之前持久化的对话历史
            self._restore_memory()
            self._trace("loop_start", {"iter": iter_count, "plan": plan}, "")
            out_answer = None
            for step in plan:
                # 通过 Agent普通工具调用
                try:
                    out_answer = self.agent.invoke({"messages": [("user", step)]},
                        config={
                            "recursion_limit": self.agent_recursion_limit
                        })
                    aggregated.append({"step":step,"output":_safe_serialize(out_answer)})
                    self._trace("executor_agent", {"step":step}, out_answer)
                except Exception as e:
                    # 如果报错（通常是tool调用出错，则不调用tool继续执行）
                    logging.error({"step":step,"output":str(e)})
                    continue 
            
            answer_content = "" if not out_answer else json.dumps(out_answer['messages'][-1].content, ensure_ascii=False)
            
            # 删除可能的think标签
            answer_content = self.remove_think(answer_content)   

            # Evaluator
            eval_prompt = f"""
            你是 Evaluator，判断<检索结果>是否充分回答<用户问题>,判断的依据是：根据你的专业知识，判断答案的含义是否与用户问题基本在一个维度上。
            1. 如果仅仅能部分回答时用户的问题，则返回 基本充分
            2. 如果完全能够回答用户的问题，请返回 完全充分
            3. 否则进行以下动作：
            将用户的问题进行重新组织，再去检索知识库，提高检索的准确率。例如之前<用户问题>为：合肥有什么好吃的呀？，则返回：请通过知识库检索，"合肥 美食"。
            注意：只可以将原问题中的句子分解成词，或者变成同义词，但是不要添加额外的词。
            
            <用户问题>{user_query['origin']}</用户问题>
            <检索结果>
            {answer_content}
            </检索结果>
            """
            eval_resp = self.llm.invoke(eval_prompt)
            decision_text = eval_resp.content
            self._trace("evaluator", {"aggregated_count":len(aggregated)}, decision_text)
            
            # 删除可能的think标签
            decision_text = self.remove_think(decision_text)
            
            logging.info(f'检索结果是否充分评估结果：{decision_text}')

            if "完全充分" in decision_text.lower() or "基本充分" in decision_text.lower():
                answer_prompt = f"""
                你是 Answer Composer，请基于聚合结果生成回答：
                用户问题：{user_query['origin']}
                检索结果：
                {answer_content}
                充分性评价：{decision_text}
                输出自然语言答案。
                注意：
                - 保留refrence和tools信息
                - 语句要通顺专业，围绕用户问题的主题来进行语言组织。
                - 答案文本中不要包含任何引用数据，调用工具的内容，这些内容在返回数据的 refrences 和 tools 字段中显示。
                - 最终格式如下: {{ "content": 答案文本, "references": {{"documentId": "xxx", "segmentId": "xxxx", "file": "xxx"}}, "tools": [tools] }}
                注意： 
                - 要返回严格的json对象字符串，不要返回任何其他多余的文本内容。
                - 如果 充分性评价 为 完全充分，则返回最终的答案；如果是 基本充分 需要说明缺少的信息以及解释缺少信息的原因。
                """
                final_answer = self.llm.invoke(answer_prompt)
                self._trace("compose_answer", {}, final_answer)
                self.persist()
                return {"status":"ok","answer":final_answer,"trace":self.trace}
            else:
                plan = [decision_text.splitlines()[0]]
                logging.info(f"[检索结果  [{answer_content}] 不满足，重新制检索计划,第 {iter_count + 1} 次] {decision_text}")
                self._trace("plan_updated", {"new_plan":plan}, decision_text)

        self._trace("max_iters_exceeded", {}, "")
        self.persist()
        
        # 告诉用户为何不满足
        failed_answer_prompt = f"""
        你是 Answer Composer，请基于检索结果生成回答：
        用户问题：{user_query['origin']}
        检索结果：
        {answer_content}
        输出自然语言答案。
        注意：
        - 因为检索结果不符合用户问题，所以请说明原因。
        - 仅保留说明文字即可,将引用来源、实用工具等信息都去除掉。
        
        *** 最终的数据格式如下: 
        {{ "content": 答案文本, "references": {{"documentId": "xxx", "segmentId": "xxxx", "file": "xxx"}}, "tools": [tools] }}
        """
        failed_answer = self.llm.invoke(failed_answer_prompt)
        return {"answer": failed_answer}

    def persist(self):
        key = f"run:{self.run_id}"
        payload = {"trace":self.trace}
        self.persistor.save(key, payload)

# -------------------------------
# Demo
# -------------------------------

# 清理返回数据
def get_json_from_answer(content):
    import re
    answer = content
    
    # 清除可能的json markdown 外壳
    pattern = r"```json(.*?)```"
    match = re.search(pattern, answer, re.DOTALL)
    if match:
        answer = match.group(1).strip()
    else:
        # 可能前面有特殊字符
        # 删除第一个大括号前面所有的字符
        idx = answer.find("{")
        if (idx != -1):
            answer = answer[idx:].strip()
    return answer

def demo():
    agent_llm = ChatOpenAI(
        # api_key="123",
        temperature=0,
        max_retries=3,
        base_url=f"{MODEL_URL}",
        model=f"{MODEL_NAME}"
    )

    api_tools_name = [
        '能耗数据统计', '运营数据统计', '安防数据统计'
    ]
    
    datasets_tools_name = [
        'query_knowledge_base',
        'read_file_chunks', 
        'list_datasets', 'list_files'
    ]
    
    SYSTEM_PROMPT = f"""你是一个智能助手，能使用工具回答用户问题。
    * 如果用户要求检索知识库，请使用以下几个工具来进行检索:{','.join(datasets_tools_name)}
    遵循以下步骤：
    1. 用 query_knowledge_base 搜索知识库中相关内容，获得候选文件和片段线索，结果中请选取最符合用户问题的片段来作为证据。
    {'''
    2. 使用 read_file_chunks 精读最相关的2-3个片段内容作为证据。具体做法是:
    - 先获取第一步检索到的内容的chunk编号
    - 判断内容，决定你要向前检索还是向后检索
    - 如果向前检索，则 read_file_chunks 的 start_chunk_id 则设置为当前检索到文件的chunk编号小的数字,实际可以减去2或者3
    - 如果向后检索，则 read_file_chunks 的 start_chunk_id 则设置为当前检索到文件的chunk编号大的数字,实际可以加上2或者3
    - 从返回的文本结果中，找出最适合回答用户问题的答案，通过语言组织之后返回。
    注意： 不要编造没有检索到的内容。
    ''' if 1 else ''}
    3. 回答末尾注明 refrences: {{documentId: response.documentId, segmentId: response.segmentId}}
    4. 回答末尾注明 tools: 调用的工具列表
    5. 回家末尾注明 file: {{file_name}}
    *** 最终的数据格式如下: 
    - 最终格式如下: {{ "content": 答案文本, "references": {{"documentId": "xxx", "segmentId": "xxxx", "file": "xxx"}}, "tools": [tools] }}

    重要规则：
    - 如果检索知识库的结果为空，例如 
    query_knowledge_base 返回为空数组 [] 或读取的文件片段内容为空，请不要继续调用其他工具，也不要根据自己的理解生成答案；
    请直接回答："未检索到相关内容，知识库中缺少相关信息。"
    - 你的所有回答都必须基于实际读取到的片段。
    - 若找不到足够的证据，将你检索到的内容通过文本组织成可读内容返回即可。
    - 优先选择评分高的搜索结果进行深入阅读。
    - 如果实在找不到答案，就回答"未检索到相关内容，知识库中缺少相关信息。"。
    
    * 如果用户要求查询API，请使用以下几个工具来进行检索:{','.join(api_tools_name)}。你的任务是:
    - 根据要求组合查询条件，并从工具中选择合适的工具进行查询
    - 将工具查询结果数据通过专业的语言转达给用户
    对于查询条件数据中的字段，说明如下：
    - area: 如果是整个园区，则值为'park';如果是楼层，则值为'B1F','1F','2F'等;
    - start_date: 查询开始时间，格式为YYYY-MM-DD
    - end_date: 查询结束时间，格式为YYYY-MM-DD
    - groupby: 如果是按区域统计，则为'area', 如果按公司统计，则为'company', 如果按时间统计，则为'time'
    - 如果没有满足条件的API，可以放弃API查询环节，直接使用知识库检索的结果来回答问题。
    
    工具列表：{{tools}}
    工具名称：{{tool_names}}
    思考记录：{{agent_scratchpad}}
    用户问题：{{input}}
    """

    # 直接使用 @tool 装饰器的函数
    tools = [query_knowledge_base, 
            read_file_chunks, 
            list_datasets, list_files
            # , 能耗数据统计, 运营数据统计, 安防数据统计
            ]
    
    # persistor = Persistor(method="sqlite", sqlite_path="agent_state.db")
    persistor = Persistor()

    engine = LCWorkflowEngine(llm=agent_llm, tools=tools, persistor=persistor, run_id="d08cb46d-71ea-4459-b7cb-5f8187ab8cf1",
                            system_prompt=SYSTEM_PROMPT
    )
    
    query = {"origin": "以人为本，安全第一"}
    query['prompt'] = f'请通过知识库检索:{query["origin"]}'
    
    res = engine.run(query)
    answer = res['answer'].content
    
    # 清理返回数据
    answer = get_json_from_answer(answer)

    answer_json = json.loads(answer)
    print(answer_json)

if __name__=="__main__":
    demo()