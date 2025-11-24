# memory/store.py
import os, json, time
from langchain_classic.memory import ConversationBufferMemory
from typing import Dict

class Persistor:
    """简单 JSON 持久化"""
    def __init__(self, path="memory_store.json"):
        self.path = path

    def save(self, key: str, data: dict):
        all_data = {}
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    all_data = json.load(f)
                except json.JSONDecodeError:
                    all_data = {}
        all_data[key] = {
            "timestamp": time.time(),
            "data": data
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

    def load(self, key: str):
        if not os.path.exists(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                all_data = json.load(f)
            except json.JSONDecodeError:
                return None
        return all_data.get(key, {}).get("data")


class MemoryStore:
    """
    多用户 memory 管理 + 自动持久化 trace
    """
    def __init__(self, persistor_path="memory_store.json"):
        self.store: Dict[str, ConversationBufferMemory] = {}
        self.trace: Dict[str, list] = {}
        self.persistor = Persistor(path=persistor_path)

    def get_memory(self, user_id: str):
        if user_id not in self.store:
            self.store[user_id] = ConversationBufferMemory(memory_key="chat_history")
            saved = self.persistor.load(user_id)
            if saved:
                # 恢复对话
                for msg in saved.get("messages", []):
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "user":
                        self.store[user_id].chat_memory.add_user_message(content)
                    elif role == "ai":
                        self.store[user_id].chat_memory.add_ai_message(content)
                # 恢复 trace
                self.trace[user_id] = saved.get("trace", [])
            else:
                self.trace[user_id] = []
        return self.store[user_id]

    def append_trace(self, user_id: str, phase: str, meta: dict, output: str):
        if user_id not in self.trace:
            self.trace[user_id] = []
        self.trace[user_id].append({
            "ts": time.time(),
            "phase": phase,
            "meta": meta,
            "output": output
        })
        self._persist_user(user_id)

    def _persist_user(self, user_id: str):
        """
        保存 memory 和 trace 到 JSON
        """
        mem = self.store[user_id]
        messages = []
        for msg in mem.chat_memory.messages:
            if msg.type == "human":
                messages.append({"role": "user", "content": msg.content})
            elif msg.type == "ai":
                messages.append({"role": "ai", "content": msg.content})
        data = {
            "messages": messages,
            "trace": self.trace.get(user_id, [])
        }
        self.persistor.save(user_id, data)