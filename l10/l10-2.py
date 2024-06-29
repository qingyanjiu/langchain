'''
通过Memory记住客户上次买花时的对话细节
ConversationChain + ConversationBufferWindowMemory
ConversationBufferWindowMemory 是缓冲窗口记忆，它的思路就是只保存最新最近的几次人类和 AI 的互动。
因此，它在之前的“缓冲记忆”基础上增加了一个窗口值 k。这意味着我们只保留一定数量的过去互动，然后“忘记”之前的互动
'''

from langchain.chains.conversation.base import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory

# 初始化大语言模型
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)

# 初始化对话链
conversation = ConversationChain(llm=llm, memory=ConversationBufferWindowMemory(k=1))

# 第一天的对话
# # 回合1
result = conversation.invoke("我姐姐明天要过生日，我需要一束生日花束。")
print(result)

# 回合2
result = conversation.invoke("她喜欢粉色玫瑰，颜色是粉色的。")
print(result)

# 回合3 （第二天的对话）
result = conversation.invoke("我又来了，还记得我昨天为什么要来买花吗？")
print(result)