"""
Agentic RAG MVP 示例
实现一个最小可用的 Agentic RAG 系统，演示如何通过工具组合实现"先粗后细"的证据收集策略
"""

from typing import List, Dict
import json
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import requests


# ======== 1. 定义 Dify 知识库访问控制器 ========
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


# ======== 2. 初始化知识库控制器 ========
kb_controller = DifyKnowledgeBaseController(
    base_url="http://localhost",
    api_key="dataset-XqsUQ5VQWkejtgJHFzEsZLar",
    dataset_id="c5153abf-19b3-429b-9902-812dd85c8bfc"
)


# ======== 3. 定义工具函数（直接映射到 kb_controller 方法） ========

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


# ======== 4. 创建 Agentic RAG 系统 ========
def create_agentic_rag_system():
    """创建 Agentic RAG 系统"""

    tools = [query_knowledge_base, read_file_chunks, list_files]

    SYSTEM_PROMPT = """你是一个 Agentic RAG 助手。请遵循以下策略逐步收集证据后回答：

1. 用 query_knowledge_base 搜索知识库中相关内容，获得候选文件和片段线索
2. 使用 read_file_chunks 精读最相关的2-3个片段内容作为证据
3. 基于读取的具体片段内容组织答案
4. 回答末尾用"引用："格式列出实际读取的fileId和chunkIndex
5. 回答末尾用"调用："格式列出实际调用的tool和参数

重要规则：
- 如果 query_knowledge_base 返回为空数组 [] 或读取的文件片段内容为空，
  *请不要继续调用其他工具，也不要编造答案。
  *请直接回答："知识库中缺少相关信息，建议补充相关文档。"
- 你的所有回答都必须基于实际读取到的片段。
- 若找不到足够的证据，就明确说明“知识库中暂缺相关信息”。
- 优先选择评分高的搜索结果进行深入阅读。
- 如果实在找不到答案，就回答你不知道。
"""

    llm = ChatOpenAI(
        temperature=0,
        max_retries=3,
        api_key="123",
        base_url="http://localhost:1234/v1/",
        model="google/gemma-3-12b",
    )

    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
    return agent


# ======== 5. 主程序 ========
def main():
    print("🚀 初始化 Agentic RAG 系统...")
    agent = create_agentic_rag_system()

    print("\n📚 知识库列表：")
    datasets = kb_controller.list_datasets()
    for dataset in datasets:
        print(f"  - {dataset.get('id')} | {dataset.get('name')} | 文档数: {dataset.get('document_count', '未知')}")
        documents = kb_controller.list_files(dataset.get('id'))
        for document in documents:
            print("\n📚 文档列表：")
            print(f"  - {document.get('id')} | {document.get('name')} | token数: {document.get('tokens', '未知')}")
    

    print("\n" + "=" * 80)
    print("💬 开始问答演示")
    print("=" * 80)

    question = "请基于知识库，概述 RAG 的优缺点，并给出引用。"
    print(f"\n❓ 问题: {question}")
    print("\n🤔 Agent 思考与行动过程:")
    print("-" * 50)

    
    result = agent.invoke({"messages": [("user", question)]},
                        config={
                            "recursion_limit": 10
                        })
    print("======")
    try:
        print(json.dumps(result, ensure_ascii=False, indent=2))['messages']
    except Exception as e:
        print(result['messages'])


if __name__ == "__main__":
    main()