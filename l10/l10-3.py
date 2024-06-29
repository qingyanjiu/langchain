'''
通过Memory记住客户上次买花时的对话细节
ConversationChain + ConversationSummaryMemory
ConversationSummaryMemory（对话总结记忆）的思路就是将对话历史进行汇总，然后再传递给 {history} 参数。
这种方法旨在通过对之前的对话进行汇总来避免过度使用 Token。
ConversationSummaryMemory 有这么几个核心特点。
1.汇总对话：此方法不是保存整个对话历史，而是每次新的互动发生时对其进行汇总，然后将其添加到之前所有互动的“运行汇总”中。
2.使用 LLM 进行汇总：该汇总功能由另一个 LLM 驱动，这意味着对话的汇总实际上是由 AI 自己进行的。
3.适合长对话：对于长对话，此方法的优势尤为明显。虽然最初使用的 Token 数量较多，但随着对话的进展，汇总方法的增长速度会减慢。与此同时，常规的缓冲内存模型会继续线性增长。
'''

from langchain.chains.conversation.base import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryMemory

# 初始化大语言模型
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)

# 初始化对话链
conversation = ConversationChain(llm=llm, memory=ConversationSummaryMemory(llm=llm))

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