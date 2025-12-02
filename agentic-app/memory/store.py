# memory/store.py
import os, json, time
from langchain_core.messages import BaseMessage
from langchain_classic.memory.chat_memory import BaseChatMemory
from langchain_classic.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from typing import Dict

class Persistor:
    """简单 JSON 持久化"""
    def __init__(self, path="memory_store.json"):
        self.path = path

    # 持久化历史对话记录
    def save(self, user_id: str, session_id: str, data: dict):
        all_data = {}
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    all_data = json.load(f)
                except json.JSONDecodeError:
                    all_data = {}
        if (user_id not in all_data):
            all_data[user_id] = {}
        all_data[user_id][session_id] = {
            "timestamp": time.time(),
            "data": data
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

    # 从持久化存储读取历史对话记录
    def load(self, user_id: str, session_id):
        if not os.path.exists(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                all_data = json.load(f)
            except json.JSONDecodeError:
                return None
        return all_data.get(user_id, {}).get(session_id, {}).get("data")


class MemoryStore:
    """
    多用户 memory 管理 + 自动持久化 memory (@@@@ TODO 现在是写文件，要改成写数据库最好)
    """
    def __init__(self, persistor_path="memory_store.json"):
        self.store: BaseChatMemory
        self.persistor = Persistor(path=persistor_path)

    # 从持久化存储读取以前的聊天记录
    def get_memory(self, user_id: str, session_id: str):
        memory = ConversationBufferWindowMemory(
            k=3,
            memory_key="chat_history", 
            return_messages=True
        )
        # 赋值新memory对象s
        self.store = memory
        # 从持久化数据读取，并填充数据到memory对象
        saved = self.persistor.load(user_id, session_id)
        if saved:
            # 恢复对话
            for msg in saved.get("messages", []):
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    self.store.chat_memory.add_user_message(content)
                elif role == "ai":
                    self.store.chat_memory.add_ai_message(content)
        return self.store

    def persist_user(self, user_id: str, session_id: str):
        """
        保存 memory 和 trace 到 JSON
        """
        messages = []
        for msg in self.store.chat_memory.messages:
            if msg.type == "human":
                messages.append({"role": "user", "content": msg.content})
            elif msg.type == "ai":
                messages.append({"role": "ai", "content": msg.content})
        data = {
            "messages": messages,
        }
        self.persistor.save(user_id, session_id, data)