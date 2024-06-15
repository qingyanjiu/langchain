# 1.Load 导入Document Loaders
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import TextLoader
import os

# 加载Documents
base_dir = '/Users/louisliu/Documents/coder/project/langchain/docs' # 文档的存放目录
documents = []
for file in os.listdir(base_dir): 
    # 构建完整的文件路径
    file_path = os.path.join(base_dir, file)
    if file.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith('.docx'): 
        loader = Docx2txtLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith('.txt'):
        loader = TextLoader(file_path)
        documents.extend(loader.load())

# 2.Split 将Documents切分成块以便后续进行嵌入和向量存储
from langchain.text_splitter import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
chunked_documents = text_splitter.split_documents(documents)

# 3.Store 将分割嵌入并存储在矢量数据库Qdrant中 
# pip install qdrant-client -i https://pypi.tuna.tsinghua.edu.cn/simple
# pip install sentence_transformers -i https://pypi.tuna.tsinghua.edu.cn/simple
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
 
bge_embeddings = HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-zh-v1.5")

vectorstore = Qdrant.from_documents(
    documents=chunked_documents, # 以分块的文档
    embedding=bge_embeddings, # 用OpenAI的Embedding Model做嵌入
    location=":memory:",  # in-memory 存储
    collection_name="my_documents",) # 指定collection_name


# 4. Retrieval 准备模型和Retrieval链
import logging # 导入Logging工具
from langchain_community.llms import Ollama
from langchain.retrievers.multi_query import MultiQueryRetriever # MultiQueryRetriever工具
from langchain.chains import RetrievalQA # RetrievalQA链

# 设置Logging
logging.basicConfig()
logging.getLogger('langchain.retrievers.multi_query').setLevel(logging.INFO)

# 实例化一个大模型工具
llm = Ollama(base_url='http://192.168.100.85:11434', model="llama3-cn", temperature=0)

# 实例化一个MultiQueryRetriever
retriever_from_llm = MultiQueryRetriever.from_llm(retriever=vectorstore.as_retriever(), llm=llm)

# 实例化一个RetrievalQA链
qa_chain = RetrievalQA.from_chain_type(llm,retriever=retriever_from_llm)


# result = qa_chain.invoke({"query": "像素流的优势是什么"})
result = qa_chain.invoke({"query": "手势识别控制是什么"})
print(result)