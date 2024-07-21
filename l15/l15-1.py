'''
检索增强生成：RAG
'''
# 1.Load 导入Document Loaders
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import TextLoader
import os


from langchain_community.embeddings import HuggingFaceBgeEmbeddings
 
# 此处需要设置代理翻墙 huggingface你懂的。先挂v2ray代理
# os.environ['https_proxy'] = 'http://localhost:10809'
# embeddings_model = HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-zh-v1.5")
embeddings_model = HuggingFaceBgeEmbeddings(model_name=r"C:\Users\louis\.cache\huggingface\hub\models--BAAI--bge-large-zh-v1.5\snapshots\79e7739b6ab944e86d6171e44d24c997fc1e0116")

embeddings = embeddings_model.embed_documents(
    [
        "您好，有什么需要帮忙的吗？",
        "哦，你好！昨天我订的花几天送达",
        "请您提供一些订单号？",
        "12345678",
    ]
)
print(len(embeddings), len(embeddings[0]))

embedded_query = embeddings_model.embed_query("刚才对话中的订单号是多少?")
print(embedded_query[:3])



'''========================================================'''


# 导入内存存储库，该库允许我们在RAM中临时存储数据
from langchain.storage import InMemoryStore
from langchain.vectorstores import DocArrayInMemorySearch

# 创建一个InMemoryStore的实例
store = InMemoryStore()

# 导入与嵌入相关的库。OpenAIEmbeddings是用于生成嵌入的工具，而CacheBackedEmbeddings允许我们缓存这些嵌入
from langchain.embeddings import CacheBackedEmbeddings


# 创建一个CacheBackedEmbeddings的实例。
# 这将为underlying_embeddings提供缓存功能，嵌入会被存储在上面创建的InMemoryStore中。
# 我们还为缓存指定了一个命名空间，以确保不同的嵌入模型之间不会出现冲突。
embedder = CacheBackedEmbeddings.from_bytes_store(
    embeddings_model,  # 实际生成嵌入的工具
    store,  # 嵌入的缓存位置
    namespace=embeddings_model.model_name  # 嵌入缓存的命名空间
)

# 使用embedder为两段文本生成嵌入。
# 结果，即嵌入向量，将被存储在上面定义的内存存储中。
embeddings = embedder.embed_documents(["你好", "智能鲜花客服"])


'''========================================================'''
# pip install bilibili-api-python -i https://pypi.tuna.tsinghua.edu.cn/simple
# 导入文档加载器模块，并使用TextLoader来加载文本文件
# ******** 各种loader https://python.langchain.com/v0.2/docs/integrations/document_loaders/ ***********

from langchain_community.document_loaders import TextLoader, BiliBiliLoader
loader = TextLoader(r'C:\Users\louis\Desktop\111.txt', encoding='utf8')

# 获取bilibili视频字幕信息（视频必须由字幕）
# 以下三个参数从request的header中获取
# SESSDATA = "775139df%2C1736778051%2Cee9e3%2A71CjDbndC7TE1FKrnDNMSyIpxRGngJXIr_xFeb-PKos5JtESltQPLWtEDgnks4-WTpg6kSVjVuRnBOZDdpd3ZKcU5oemVKcGY2UXFZc1d2ZEllU3lNb1YxYWhyMkk4RXJHWlJRdk5YYnZZNy1UQnBpRzNVQ0JYb3p2VFVXUG44Y0kxSjZXSG9jQ0ZnIIEC"
# BUVID3 = "CC9733EC-1513-1FB4-2721-0297FE2C9E1196160infoc"
# BILI_JCT = "a1f19710a29dbd679c4d23c278e4496d"
# loader = BiliBiliLoader(
#     [
#         "https://www.bilibili.com/video/BV1zZ421T78c/",
#     ],
#     sessdata=SESSDATA,
#     bili_jct=BILI_JCT,
#     buvid3=BUVID3,
# )
# print(loader.load())

# 使用VectorstoreIndexCreator来从加载器创建索引
from langchain.indexes import VectorstoreIndexCreator
index = VectorstoreIndexCreator(embedding=embeddings_model).from_loaders([loader])

# 讯飞星火
os.environ["IFLYTEK_SPARK_APP_ID"] = "5af89b1c"
os.environ["IFLYTEK_SPARK_API_KEY"] = "a21950a0e2f8d21eeaf0cf136ea34417"
os.environ["IFLYTEK_SPARK_API_SECRET"] = "ZGQ1NjMzMDQxZWMzYmIyNDRkZmI5MGYy"
from langchain_community.llms import SparkLLM
# Load the model
llm = SparkLLM()

# 定义查询字符串, 使用创建的索引执行查询
query = "如何下载模型"
result = index.query(query, llm=llm)
print(result) # 打印查询结果


# # 自定义文本分割器、向量存储以及向量嵌入
# from langchain.text_splitter import CharacterTextSplitter
# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# from langchain.vectorstores import Chroma
# index_creator = VectorstoreIndexCreator(
#     vectorstore_cls=Chroma,
#     embedding=embeddings_model,
#     text_splitter=text_splitter
# )
# index = index_creator.from_loaders([loader])