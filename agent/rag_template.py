# agentic_workflow_enhanced.py
"""
增强版 Agent 工作流（Python）
功能：
- Planner -> Executor -> Evaluator 三段式流程
- 工具注册与路由（规则 + LLM 判定混合）
- Executor 支持 RAG 流水线（query -> read_chunks）
- 并行执行工具（ThreadPoolExecutor）
- 日志/trace 与状态持久化：JSON / SQLite / Redis
- 简单记忆（MemoryNode）
- 重试与错误处理、超时
- 可以切换 MockLLM 或 真实 ChatOpenAI（示例）


使用/部署说明（要点）
1.	如果要用真实 LLM：
•	将 use_real_llm = True，并在 ChatOpenAIWrapper(...) 中传入真实 SDK 初始化参数（api_key, model, base_url 等）。
•	ChatOpenAIWrapper 是轻量封装，具体如何调用你使用的 SDK（langchain_openai、openai、或其他）需要做小修改以匹配其 API（例如 client.chat、client.invoke 等）。
2.	工具替换：
•	把 mock_query_knowledge_base 与 mock_read_file_chunks 替换为你实际的知识库检索 / 文档读取函数（保持返回格式兼容，检索返回 records，读文档返回 chunks）。
•	建议检索函数返回 records 数组，每条记录包含 file_id, chunk_index, score, text。
3.	路由器（规则 + LLM）
•	ToolRegistry.route 先做关键词规则匹配，若不足再调用 LLM（llm_router）建议工具名。你可以扩展 LLM prompt 让它返回 JSON 或更结构化的结果以便解析。
4.	RAG 流水线
•	executor_rag_pipeline 自动把检索结果的 topK 文档传给 read_file_chunks（或其它读取工具）进行精读，这是你要的「先粗后细」策略。
5.	持久化
•	Persistor 支持三种方式：JSON 文件、SQLite（适合单机持久化）、Redis（适合分布式）。根据生产环境选择。Redis 用于多实例协同时非常有用。
6.	扩展点
•	可将 executor_rag_pipeline 增强为并行处理多个 query、或将 read_file_chunks 的读取细化为按 chunkIndex 精读并评分后只保留最有价值片段。
•	可加入 token/cost 监控、Prometheus 指标、错误告警等。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import json, time, uuid, traceback, sqlite3, os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Redis 是可选依赖，如果没有安装会回退到文件/SQLite
try:
    import redis
except Exception:
    redis = None

# 如果你使用 langchain_openai 的 ChatOpenAI，请按需替换导入
# 下面的 ChatOpenAI 演示用占位（若未安装，请使用 MockLLM）
try:
    from langchain_openai import ChatOpenAI  # 如无此包，请使用 MockLLM 或替换为你的 LLM SDK
except Exception:
    ChatOpenAI = None

# -------------------------------
# LLM 接口 & 实现
# -------------------------------
class LLMInterface:
    def invoke(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        messages: [{'role': 'system'|'user'|'assistant', 'content': '...'}, ...]
        返回: {'content': 'model text', ...}
        """
        raise NotImplementedError

class MockLLM(LLMInterface):
    def invoke(self, messages):
        # 基于最后 user 消息简单回应（便于脱网调试）
        last_user = [m for m in messages if m['role']=='user'][-1]['content']
        if '生成计划' in last_user or 'plan' in last_user or '规划' in last_user:
            return {'content': "1. 在知识库中检索相关文档\n2. 精读 top2 文档段落\n3. 汇总并给出结论"}
        if '评估' in last_user or '是否充分' in last_user:
            return {'content': "评估结果：证据充分，可以回答。"}
        return {'content': "MockLLM 回应：已收到请求，返回模拟文本。"}

class ChatOpenAIWrapper(LLMInterface):
    """
    用法示例：请确保你已安装并配置好对应的 SDK（此处以 langchain_openai.ChatOpenAI 为例）。
    构造时传入与该 SDK 对应的参数（api_key, base_url, model 等）。
    """
    def __init__(self, **kwargs):
        if ChatOpenAI is None:
            raise RuntimeError("ChatOpenAI SDK 未找到，请安装或使用 MockLLM。")
        # ChatOpenAI 的构造参数视具体包版本而定，请替换下列示例为你环境的实际初始化
        self.client = ChatOpenAI(**kwargs)

    def invoke(self, messages: List[Dict[str,str]]) -> Dict[str, Any]:
        # 将 messages 转成 sdk 所需格式并调用
        # 这里假设 client.invoke 或 client.chat 方法返回 .content 或 .text
        # 你需要根据所用 SDK 做微调
        # 示例（伪代码）：
        resp = self.client.invoke(messages) if hasattr(self.client, "invoke") else self.client(messages)
        # 规范化返回
        if isinstance(resp, dict) and 'content' in resp:
            return resp
        # 尝试从对象中提取文本
        text = getattr(resp, 'content', None) or getattr(resp, 'text', None) or str(resp)
        return {'content': text}

# -------------------------------
# Tool / ToolRegistry
# -------------------------------
@dataclass
class Tool:
    name: str
    func: Callable[..., Any]
    tags: List[str] = field(default_factory=list)
    description: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

class ToolRegistry:
    def __init__(self, llm_router: Optional[LLMInterface]=None):
        self._tools: Dict[str, Tool] = {}
        self.llm_router = llm_router  # 如果存在，用来做复杂路由判断

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list(self):
        return list(self._tools.keys())

    def route(self, intent: str, top_k: int = 3) -> List[Tool]:
        """
        混合路由策略：
         1) 简单规则匹配（关键词）
         2) 若未命中且 llm_router 可用，则调用 LLM 给出推荐工具列表（按名称/理由）
        返回匹配到的工具列表（最多 top_k）
        """
        intent_lower = intent.lower()
        matches = []
        # 规则匹配：tool name 或 description 中包含关键词
        for t in self._tools.values():
            if any(k in intent_lower for k in t.name.lower().split('_')) or any(k.lower() in intent_lower for k in t.tags):
                matches.append(t)
        # 如果规则匹配不足且提供了 llm_router，则让 LLM 给出建议
        if len(matches) < top_k and self.llm_router is not None:
            # 构造 prompt 请求 LLM 推荐工具名（简单格式化）
            system = {"role":"system", "content":"你是一个工具路由器。请根据用户意图返回最相关的工具名称列表，按照优先级用逗号分隔。"}
            user = {"role":"user", "content": f"用户意图：{intent}\n已有工具：{','.join(self.list())}\n请返回最多 {top_k} 个最相关工具名，逗号分隔，严谨且不要多余说明。"}
            try:
                rsp = self.llm_router.invoke([system, user])
                txt = rsp.get("content","")
                # 从 LLM 输出中解析工具名
                candidates = [s.strip() for s in txt.replace('\n',',').split(',') if s.strip()]
                for name in candidates:
                    if name in self._tools and self._tools[name] not in matches:
                        matches.append(self._tools[name])
                        if len(matches) >= top_k:
                            break
            except Exception:
                pass
        # 最终返回 top_k
        if not matches:
            # 兜底：返回所有带 'query' 或 'read' 的工具优先
            matches = [t for t in self._tools.values() if 'query' in t.name.lower() or 'read' in t.name.lower()]
        return matches[:top_k]

# -------------------------------
# Persistence: JSON / SQLite / Redis
# -------------------------------
class Persistor:
    def __init__(self, method: str = "json", path: str = "agent_state.json", sqlite_path: str = "agent_state.db", redis_cfg: Dict = None):
        self.method = method.lower()
        self.path = path
        self.sqlite_path = sqlite_path
        self.redis_cfg = redis_cfg or {
            "host": "127.0.0.1",
            "port": 6379,
            "db": 0,
            "password": None,
            "decode_responses": True,
            "socket_timeout": 5,
        }
        self.redis_client = None
        if self.method == "redis" and redis is not None:
            self.redis_client = redis.Redis(**self.redis_cfg)

    def save(self, key: str, data: Dict[str, Any]):
        if self.method == "json":
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({key: data}, f, ensure_ascii=False, indent=2)
        elif self.method == "sqlite":
            conn = sqlite3.connect(self.sqlite_path)
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS agent_state (key TEXT PRIMARY KEY, payload TEXT, updated_at REAL)""")
            payload = json.dumps(data, ensure_ascii=False)
            c.execute("REPLACE INTO agent_state (key, payload, updated_at) VALUES (?,?,?)", (key, payload, time.time()))
            conn.commit()
            conn.close()
        elif self.method == "redis" and self.redis_client:
            self.redis_client.set(key, json.dumps(data, ensure_ascii=False))
        else:
            # fallback to json
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({key: data}, f, ensure_ascii=False, indent=2)

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        if self.method == "json":
            if not os.path.exists(self.path): return None
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d.get(key)
        elif self.method == "sqlite":
            conn = sqlite3.connect(self.sqlite_path)
            c = conn.cursor()
            c.execute("SELECT payload FROM agent_state WHERE key=?", (key,))
            row = c.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
            return None
        elif self.method == "redis" and self.redis_client:
            v = self.redis_client.get(key)
            return json.loads(v) if v else None
        else:
            return None

# -------------------------------
# WorkflowEngine（带 RAG 流水线）
# -------------------------------
class WorkflowEngine:
    def __init__(self, llm: LLMInterface, tool_registry: ToolRegistry, persistor: Persistor, max_iters: int = 3):
        self.llm = llm
        self.tool_registry = tool_registry
        self.persistor = persistor
        self.max_iters = max_iters
        self.run_id = str(uuid.uuid4())
        self.trace: List[Dict[str, Any]] = []
        self.memory = {}

    def _trace(self, phase: str, meta: Dict[str, Any], output: Any):
        rec = {"ts": time.time(), "phase": phase, "meta": meta, "output": output}
        self.trace.append(rec)

    def planner(self, user_query: str) -> List[str]:
        system = {"role":"system","content":"你是 Planner，生成 2-5 步可执行计划，简洁条理。"}
        user = {"role":"user","content":f"请为任务生成执行计划：{user_query}\n要求：2-5 个步骤，每步尽量可执行（例如：检索、读取、汇总、外呼）。"}
        resp = self.llm.invoke([system, user])
        plan_text = resp.get("content","")
        self._trace("planner", {"query": user_query}, plan_text)
        steps = [line.strip().lstrip("0123456789. ").strip() for line in plan_text.splitlines() if line.strip()]
        if not steps:
            steps = [plan_text]
        return steps

    def _safe_call_tool(self, tool_obj: Tool, arg: Any):
        try:
            return {"ok": True, "result": tool_obj.func(arg)}
        except Exception as e:
            try:
                time.sleep(0.5)
                return {"ok": True, "result": tool_obj.func(arg)}
            except Exception as e2:
                return {"ok": False, "error": str(e2), "traceback": traceback.format_exc()}

    def executor_rag_pipeline(self, query_step: str, top_k_docs: int = 2) -> Dict[str, Any]:
        """
        RAG 专用流水线：
        1) 调用 query_knowledge_base（或其他检索类工具）获取候选片段（records）
        2) 选择 top_k_docs 高分记录，调用 read_file_chunks（或等价工具）获取精读内容
        3) 返回聚合结果
        """
        # 先路由到检索工具
        candidate_tools = self.tool_registry.route(query_step)
        # 找到检索类工具优先（名字中包含 'query' 或 'search'）
        search_tools = [t for t in candidate_tools if 'query' in t.name.lower() or 'search' in t.name.lower()]
        if not search_tools:
            # 兜底所有工具
            search_tools = candidate_tools

        rag_agg = {"query": query_step, "retrievals": [], "reads": []}
        # 并行执行搜索工具（通常只有一个）
        for t in search_tools:
            out = self._safe_call_tool(t, query_step)
            self._trace("executor_tool_call", {"tool": t.name, "arg": query_step}, out)
            if not out.get("ok"):
                continue
            result = out["result"]
            # 约定 result 为 dict 包含 'records' 或 'hits' 等
            records = result.get("records") if isinstance(result, dict) else None
            if not records:
                # 兼容不同工具输出
                records = result.get("hits") if isinstance(result, dict) else None
            # 记录检索返回
            rag_agg["retrievals"].append({"tool": t.name, "records": records})
            # 从 records 中挑 top_k_docs（按 score 字段）
            if records:
                try:
                    sorted_rs = sorted(records, key=lambda r: float(r.get("score", 0)), reverse=True)
                except Exception:
                    sorted_rs = records
                top = sorted_rs[:top_k_docs]
                # 从 top 中提取 file_id，然后调用 read_file_chunks 工具（如果有）
                read_tool = None
                # 先尝试在 registry 中查找 read_file_chunks
                if "read_file_chunks" in self.tool_registry.list():
                    read_tool = self.tool_registry.get("read_file_chunks")
                else:
                    # 否则找名字中包含 'read' 的工具
                    for tt in self.tool_registry._tools.values():
                        if 'read' in tt.name.lower() or 'chunk' in tt.name.lower():
                            read_tool = tt
                            break
                if read_tool:
                    file_ids = []
                    # 记录要读取的 doc ids 或 chunk references（以适配不同工具）
                    for rec in top:
                        # 尝试从 record 提取 file_id 字段
                        if isinstance(rec, dict) and 'file_id' in rec:
                            file_ids.append(rec['file_id'])
                    # 调用读取工具（可传 file_ids 列表或单个 id，视工具实现）
                    if file_ids:
                        read_out = self._safe_call_tool(read_tool, file_ids)
                        self._trace("read_tool_call", {"tool": read_tool.name, "file_ids": file_ids}, read_out)
                        if read_out.get("ok"):
                            rag_agg["reads"].append({"tool": read_tool.name, "file_ids": file_ids, "content": read_out["result"]})
                else:
                    # 没有读取工具时，把 top text 直接加入 reads
                    rag_agg["reads"].append({"tool": None, "file_ids": [r.get("file_id") for r in top], "content": top})
        return rag_agg

    def executor_generic(self, step: str) -> Dict[str, Any]:
        """
        针对非 RAG 步骤的通用 executor：路由工具并并行调用
        """
        tools = self.tool_registry.route(step)
        self._trace("executor_route", {"step": step, "candidates": [t.name for t in tools]}, "")
        results = []
        if not tools:
            return {"ok": False, "error": "no_tools"}
        with ThreadPoolExecutor(max_workers=min(4, len(tools))) as ex:
            futures = {ex.submit(self._safe_call_tool, t, step): t for t in tools}
            for fut in as_completed(futures):
                t = futures[fut]
                try:
                    r = fut.result()
                except Exception as e:
                    r = {"ok": False, "error": str(e)}
                results.append({"tool": t.name, "out": r})
        self._trace("executor_results", {"step": step}, results)
        return {"ok": True, "step": step, "results": results}

    def evaluator(self, aggregated: List[Dict[str,Any]], user_query: str) -> Dict[str, Any]:
        system = {"role":"system", "content":"你是 Evaluator，判断证据是否充分并给出下一步建议（若不足）。"}
        content = f"用户问题：{user_query}\n工具聚合结果摘要：\n"
        content += json.dumps(aggregated, ensure_ascii=False, indent=2)
        user = {"role":"user", "content": content + "\n请判断是否已有足够证据回答，若足够请返回：OK。否则请给出下一步明确要执行的查询或检索指令（一句话）。并说明理由。"}
        resp = self.llm.invoke([system, user])
        decision = resp.get("content","")
        self._trace("evaluator", {"aggregated_count": len(aggregated)}, decision)
        return {"decision": decision}

    def _compose_answer(self, aggregated: List[Dict[str,Any]], user_query: str) -> str:
        # 用 LLM 汇总答案（更自然）
        system = {"role":"system", "content":"你是 Answer Composer，把工具返回的证据合成为给用户的回答，并在末尾列出引用来源（file_id/chunk）。"}
        user = {"role":"user", "content": f"用户问题：{user_query}\n工具聚合结果：\n{json.dumps(aggregated, ensure_ascii=False, indent=2)}\n请基于事实写出回答，并在末尾以 引用: [file_id:chunkIndex] 列出证据来源。"}
        resp = self.llm.invoke([system, user])
        ans = resp.get("content","")
        self._trace("compose_answer", {}, ans)
        return ans

    def run(self, user_query: str) -> Dict[str, Any]:
        key = f"run:{self.run_id}"
        # 尝试恢复
        saved = self.persistor.load(key)
        if saved:
            self.trace = saved.get("trace", [])
            self.memory = saved.get("memory", {})
        plan = self.planner(user_query)
        aggregated = []
        iter_count = 0
        while iter_count < self.max_iters:
            iter_count += 1
            self._trace("loop_start", {"iter": iter_count, "plan": plan}, "")
            for step in plan:
                # 如果步骤看起来是检索相关（包含关键词），用 RAG 流水线
                step_lower = step.lower()
                if any(k in step_lower for k in ("search", "检索", "查找", "检索知识库", "query", "retrieve", "检索文档")):
                    out = self.executor_rag_pipeline(step)
                else:
                    out = self.executor_generic(step)
                aggregated.append(out)
            # 评估
            eval_out = self.evaluator(aggregated, user_query)
            decision_text = eval_out.get("decision","").strip()
            if not decision_text:
                # 如果评估无回答，终止
                self._trace("no_eval", {}, "")
                self.persist()
                return {"status":"insufficient", "trace": self.trace}
            # 简单判断关键词确认
            if any(ok_word in decision_text.lower() for ok_word in ("ok", "可以", "充分", "足够")):
                final_answer = self._compose_answer(aggregated, user_query)
                self.memory['last_answer'] = final_answer
                self.persist()
                return {"status":"ok", "answer": final_answer, "trace": self.trace}
            else:
                # 将评估返回作为新的 plan（只取第一句作为下一步）
                plan = [decision_text.splitlines()[0]]
                self._trace("plan_updated", {"new_plan": plan}, decision_text)
                # 继续循环
        # 超出迭代次数
        self._trace("max_iters_exceeded", {}, "")
        self.persist()
        return {"status":"insufficient", "message":"多轮仍无法得到足够证据", "trace": self.trace}

    def persist(self):
        key = f"run:{self.run_id}"
        payload = {"trace": self.trace, "memory": self.memory}
        self.persistor.save(key, payload)

# -------------------------------
# 示例工具实现（请用真实实现替换）
# -------------------------------
def mock_query_knowledge_base(query: str):
    # 返回 records：{file_id, chunk_index, score, text}
    return {"records": [
        {"file_id":"docA", "chunk_index":0, "score":0.95, "text":"RAG 概念：结合检索与生成..."},
        {"file_id":"docB", "chunk_index":1, "score":0.82, "text":"检索增强生成的优点..."}
    ]}

def mock_read_file_chunks(file_ids: List[str]):
    chunks = []
    for fid in file_ids:
        chunks.append({"file_id": fid, "chunks": [
            {"chunk_index":0, "text": f"{fid} - chunk0 内容"},
            {"chunk_index":1, "text": f"{fid} - chunk1 内容"}
        ]})
    return {"chunks": chunks}

def mock_external_api(q: str):
    return {"ok": True, "result": f"外部接口返回：{q}"}

# -------------------------------
# Demo 主函数（配置示例）
# -------------------------------
def demo():
    # 选择是否使用真实 LLM（ChatOpenAI）或 Mock
    use_real_llm = False  # 改为 True 并按下述注释配置 ChatOpenAIWrapper 时使用真实模型
    if use_real_llm:
        # 示例：如何初始化 ChatOpenAIWrapper（请根据你实际 SDK 参数替换）
        llm = ChatOpenAIWrapper(api_key="YOUR_API_KEY", base_url="http://localhost:1234/v1", model="gpt-4o")
    else:
        llm = MockLLM()

    # 初始化工具注册器（并传入 llm 用作路由器）
    registry = ToolRegistry(llm_router=llm)
    registry.register(Tool(name="query_knowledge_base", func=mock_query_knowledge_base, description="query kb"))
    registry.register(Tool(name="read_file_chunks", func=mock_read_file_chunks, description="read chunks"))
    registry.register(Tool(name="external_api", func=mock_external_api, description="external api"))

    # 选择 persist 存储方式: "json" / "sqlite" / "redis"
    persist_method = "sqlite"  # 或 "json" / "redis"
    redis_cfg = {"host":"localhost", "port":6379, "db":0}  # 若使用 redis，请保证 redis 可用并已安装 redis 模块
    persistor = Persistor(method=persist_method, path="agent_state.json", sqlite_path="agent_state.db", redis_cfg=redis_cfg)

    engine = WorkflowEngine(llm=llm, tool_registry=registry, persistor=persistor, max_iters=3)
    q = "请基于知识库，概述 RAG 的优缺点，并给出引用。"
    res = engine.run(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    demo()