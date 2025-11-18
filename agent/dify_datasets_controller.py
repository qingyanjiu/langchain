import json
from dify_login_helper import DifyLoginHelper
import requests

# ======== 定义知识库控制器 ========
class DifyKnowledgeBaseController:
    def __init__(self, base_url: str, dataset_id: str):
        self.base_url = base_url.rstrip("/")
        self.dataset_id = dataset_id
        self.config_file_path = 'agent/dify-config-85.json'
        self.dify_login_helper = DifyLoginHelper(config_file_path = self.config_file_path)
        self.dify_config = self._get_config()
        self.headers = {
            "Authorization": f"Bearer {self.dify_config['datasets_api_key']}",
            "Content-Type": "application/json"
        }
    
    # 获取dify配置   
    def _get_config(self) -> dict:
        config = {}
        with open(self.config_file_path, 'r') as f:
            config = json.loads(f.read())
        return config['dify']

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

    def read_file_segments(self, doc_id: str, page: int = 1, limit: int = 1):
        """读取文档的分段内容"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents/{doc_id}/segments?status=completed&page={page}&limit={limit}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("data", [])