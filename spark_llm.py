import os
from langchain_community.llms.sparkllm import SparkLLM
# 讯飞星火
os.environ["IFLYTEK_SPARK_APP_ID"] = "5af89b1c"
os.environ["IFLYTEK_SPARK_API_KEY"] = "a21950a0e2f8d21eeaf0cf136ea34417"
os.environ["IFLYTEK_SPARK_API_SECRET"] = "ZGQ1NjMzMDQxZWMzYmIyNDRkZmI5MGYy"

def gen_spark_llm():
    # Load the model
    llm = SparkLLM(spark_api_url='wss://spark-api.xf-yun.com/v1.1/chat', spark_llm_domain='general')
    return llm