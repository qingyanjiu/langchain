'''
通过Memory记住客户上次买花时的对话细节
ConversationChain + ConversationBufferMemory
通过 ConversationBufferMemory（缓冲记忆）可以实现最简单的记忆机制
'''

from langchain.chains.conversation.base import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory

# 初始化大语言模型
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)

# 初始化对话链
conversation = ConversationChain(llm=llm, memory=ConversationBufferMemory())

# 第一天的对话
# # 回合1
conversation.invoke("我姐姐明天要过生日，我需要一束生日花束。")
print("第一次对话后的记忆:", conversation.memory.buffer)

# 回合2
conversation.invoke("她喜欢粉色玫瑰，颜色是粉色的。")
print("第二次对话后的记忆:", conversation.memory.buffer)

# 回合3 （第二天的对话）
conversation.invoke("我又来了，还记得我昨天为什么要来买花吗？")
print("/n第三次对话后时提示:/n",conversation.prompt.template)
print("/n第三次对话后的记忆:/n", conversation.memory.buffer)