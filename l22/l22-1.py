import sys
sys.path.append('.')
from spark_llm import gen_spark_llm
llm = gen_spark_llm()

# 导入所需的库和模块
from langchain.schema import HumanMessage, SystemMessage

# 定义一个命令行聊天机器人的类
class CommandlineChatbot:
    # 在初始化时，设置花卉行家的角色并初始化聊天模型
    def __init__(self):
        self.chat = llm
        self.messages = [SystemMessage(content="你是一个跑团主持人 。")]

    # 定义一个循环来持续与用户交互
    def chat_loop(self):
        print("Chatbot 已启动! 输入'exit'来退出程序。")
        while True:
            user_input = input("你: ")
            # 如果用户输入“exit”，则退出循环
            if user_input.lower() == 'exit':
                print("再见!")
                break
            # 将用户的输入添加到消息列表中，并获取机器人的响应
            self.messages.append(HumanMessage(content=user_input))
            response = self.chat.generate(self.messages)
            print(f"Chatbot: {response}")

# 如果直接运行这个脚本，启动聊天机器人
if __name__ == "__main__":
    bot = CommandlineChatbot()
    bot.chat_loop()