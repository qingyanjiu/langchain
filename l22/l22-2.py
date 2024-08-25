import sys
import asyncio

sys.path.append('.')
from spark_llm import gen_spark_llm
llm = gen_spark_llm(streaming=True)

from langchain_community.llms.ollama import Ollama
# 实例化一个大模型工具
# llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=1, verbose=True)

# 导入所需的库和模块
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ( 
                               ChatPromptTemplate, 
                               MessagesPlaceholder, 
                               SystemMessagePromptTemplate, 
                               HumanMessagePromptTemplate,
                               )
from langchain.chains.llm import LLMChain

# 带记忆的聊天机器人类
class ChatbotWithMemory:
    def __init__(self):

        # 初始化LLM
        self.llm = llm

        # 初始化Prompt
        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(
                    "你是一个程序员。你通常的回答不超过30字。"
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{question}")
            ]
        )
        
        # 初始化Memory
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # 初始化LLMChain with LLM, prompt and memory
        self.conversation = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=True,
            memory=self.memory
        )

    # 与机器人交互的函数
    def chat_loop(self):
        print("Chatbot 已启动! 输入'exit'来退出程序。")
        while True:
            user_input = input("你: ")
            if user_input.lower() == 'exit':
                print("再见!")
                break
            
            response = self.conversation({"question": user_input})
            print(f"Chatbot: {response['text']}")

if __name__ == "__main__":
    # 启动Chatbot
    bot = ChatbotWithMemory()
    bot.chat_loop()
