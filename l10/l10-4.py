'''
通过Memory记住客户上次买花时的对话细节
ConversationChain + ConversationSummaryBufferMemory
对话总结缓冲记忆，它是一种混合记忆模型，结合了上述各种记忆机制，包括 ConversationSummaryMemory 和 ConversationBufferWindowMemory 的特点。
这种模型旨在在对话中总结早期的互动，同时尽量保留最近互动中的原始内容。
它是通过 max_token_limit 这个参数做到这一点的。当最新的对话文字长度在 300 字之内的时候，LangChain 会记忆原始对话内容；
当对话文字超出了这个参数的长度，那么模型就会把所有超过预设长度的内容进行总结，以节省 Token 数量。
'''

from langchain.chains.conversation.base import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryBufferMemory
import os

# 初始化大语言模型
from langchain_community.llms.ollama import Ollama

llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0.2)


# 此处需要设置代理翻墙 load tokenizer for 'gpt2',  huggingface你懂的。先挂v2ray代理
os.environ['https_proxy'] = 'http://localhost:10809'
# 初始化对话链
conversation = ConversationChain(llm=llm, memory=ConversationSummaryBufferMemory(llm=llm, max_token_limit=300))

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