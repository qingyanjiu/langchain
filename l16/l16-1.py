'''
连接数据库
'''
# 导入sqlite3库
import sqlite3

# # 连接到数据库
conn = sqlite3.connect('FlowerShop.db')
cursor = conn.cursor()

# # 执行SQL命令来创建Flowers表
# cursor.execute('''
#         CREATE TABLE Flowers (
#             ID INTEGER PRIMARY KEY, 
#             Name TEXT NOT NULL, 
#             Type TEXT NOT NULL, 
#             Source TEXT NOT NULL, 
#             PurchasePrice REAL, 
#             SalePrice REAL,
#             StockQuantity INTEGER, 
#             SoldQuantity INTEGER, 
#             ExpiryDate DATE,  
#             Description TEXT, 
#             EntryDate DATE DEFAULT CURRENT_DATE 
#         );
#     ''')

# # 插入5种鲜花的数据
# flowers = [
#     ('Rose', 'Flower', 'France', 1.2, 2.5, 100, 10, '2023-12-31', 'A beautiful red rose'),
#     ('Tulip', 'Flower', 'Netherlands', 0.8, 2.0, 150, 25, '2023-12-31', 'A colorful tulip'),
#     ('Lily', 'Flower', 'China', 1.5, 3.0, 80, 5, '2023-12-31', 'An elegant white lily'),
#     ('Daisy', 'Flower', 'USA', 0.7, 1.8, 120, 15, '2023-12-31', 'A cheerful daisy flower'),
#     ('Orchid', 'Flower', 'Brazil', 2.0, 4.0, 50, 2, '2023-12-31', 'A delicate purple orchid')
# ]

# for flower in flowers:
#     cursor.execute('''
#         INSERT INTO Flowers (Name, Type, Source, PurchasePrice, SalePrice, StockQuantity, SoldQuantity, ExpiryDate, Description) 
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
#     ''', flower)

# # 提交更改
# conn.commit()

res = conn.execute('select * from flowers')
print(res.fetchall())

# # 关闭数据库连接
conn.close()

# pip install langchain-experimental -i https://pypi.tuna.tsinghua.edu.cn/simple

# 导入langchain的实用工具和相关的模块
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

# 连接到FlowerShop数据库（之前我们使用的是Chinook.db）
db = SQLDatabase.from_uri("sqlite:///FlowerShop.db")


import os
# 讯飞星火
os.environ["IFLYTEK_SPARK_APP_ID"] = "5af89b1c"
os.environ["IFLYTEK_SPARK_API_KEY"] = "a21950a0e2f8d21eeaf0cf136ea34417"
os.environ["IFLYTEK_SPARK_API_SECRET"] = "ZGQ1NjMzMDQxZWMzYmIyNDRkZmI5MGYy"
from langchain_community.llms import SparkLLM
# Load the model
# llm = SparkLLM()

from langchain_community.llms import Ollama
# 实例化一个大模型工具
llm = Ollama(base_url='http://localhost:11434', model="llama3-cn", temperature=0)

# 创建SQL数据库链实例，它允许我们使用LLM来查询SQL数据库
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

# 运行与鲜花运营相关的问题
# response = db_chain.invoke("有多少种不同的鲜花？")
# print(response)

# response = db_chain.invoke("哪种鲜花的存货数量最少？")
# print(response)

# response = db_chain.invoke("平均销售价格是多少？")
# print(response)

# response = db_chain.invoke("从法国进口的鲜花有多少种？")
# print(response)

# response = db_chain.invoke("哪种鲜花的销售量最高？")
# print(response)


# 用 Agent 查询数据库
# 如果大模型不够强大，agent搞不定
from langchain.utilities import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_types import AgentType

# 连接到FlowerShop数据库
db = SQLDatabase.from_uri("sqlite:///FlowerShop.db")

# 创建SQL Agent
agent_executor = create_sql_agent(
    llm=llm,
    toolkit=SQLDatabaseToolkit(db=db, llm=llm),
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)

# 使用Agent执行SQL查询

questions = [
    "哪种鲜花的存货数量最少？",
    "花的平均销售价格是多少？",
]

for question in questions:
    response = agent_executor.invoke(question)
    print(response)