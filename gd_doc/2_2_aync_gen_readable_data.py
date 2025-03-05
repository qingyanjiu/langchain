import asyncio
import os
import aiofiles
from pathlib import Path
from datetime import datetime
import time

async def llm_clean(text):

    from langchain_ollama import ChatOllama
    from langchain.callbacks.manager import CallbackManager
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

    # callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

    # ollama模型

    # llm = ChatOllama(
    #     base_url='https://c2bf-35-188-72-196.ngrok-free.app/',
    #     model="MFDoom/deepseek-r1-tool-calling:32b-qwen-distill-q4_K_M",
    #     temperature=0.1,
    # )

    # llm = ChatOllama(
    #     base_url='http://localhost:11434',
    #     model="llama3.1:8b",
    #     temperature=0.7,
    # )

    # vllm
    from langchain_openai import ChatOpenAI

    # llm = ChatOpenAI(
    #     base_url='https://shannon1997-a0m85kaya8fn-8000.gear-c1.openbayes.net/v1/',
    #     model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    #     temperature=0.7,
    #     api_key='123'
    # )

    # 阿里
    # OPENAI_API_KEY = 'sk-8e793baf80dd423e92386c2486209666'
    # llm = ChatOpenAI(model='qwen-max-2025-01-25',
    #             api_key=OPENAI_API_KEY,
    #             base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    #             temperature=0, 
    #             timeout=120
                # )

    # 硅基流动
    OPENAI_API_KEY = 'sk-sdcxstsuwiefzutgkridojrlcovgaggxddyvaicqwynpxebq'    
    llm = ChatOpenAI(model='Qwen/Qwen2.5-Coder-32B-Instruct',
                api_key=OPENAI_API_KEY,
                base_url='https://api.siliconflow.cn/v1',
                temperature=0
                )

    # response = llm.invoke("你好，你是谁？")
    # print(response.content)


    from langchain.prompts import PromptTemplate

    template  = '''
    你是一个专业的文本处理专家，擅长从markdown格式的文本中获取用户可读的通顺的文本。
    处理时请遵循以下要求：
    删掉疑似广告和宣传引流的文字内容，对于没有实质内容的文本，直接删除。
    删除作者以及编辑的署名，删除文本中的网址链接，删除文本中的电话号码，删除文本中的邮箱地址。
    删除文本中的广告词汇，删除文本中的推广性文字。
    去掉特殊字符，返回可读的文本信息。保留原有文本，和标点符号，不要进行总结和修改。保留markdown格式。
    注意：请简洁回答，不需要推理过程，回答中不要包含任何解释性的内容，如“以下是总结的内容”等。
    {text}
    '''

    # 测试打印
    prompt = PromptTemplate.from_template(template) 

    system_message = prompt.format(text=text)

    response = await llm.ainvoke(system_message)
    
    return response.content

async def process_file(file_path, semaphore):
    """
    异步处理单个文件
    :param file_path: 文件路径
    :param semaphore: 并发控制信号量
    """
    async with semaphore:  # 限制并发量
        try:
            # 异步读取文件
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                # 异步写入新文件
                output_path = os.path.join('/Users/louisliu/dev/LLM/final', file_path.name)
                # 如果文件不存在，才进行处理
                if(not os.path.exists(output_path)):
                    # 大模型处理文本信息
                    if (len(content) > 100):
                        processed_content = await llm_clean(content)
                        if len(processed_content) > 100:
                            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                                await f.write(processed_content)
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return False

async def batch_process_files(file_paths, max_concurrency=20):
    """
    批量处理文件
    :param file_paths: 文件路径列表
    :param max_concurrency: 最大并发数
    """
    # 创建输出目录
    Path('/Users/louisliu/dev/LLM/final').mkdir(exist_ok=True)
    
    # 使用信号量控制并发量
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # 创建并执行所有任务
    tasks = [process_file(fp, semaphore) for fp in file_paths]
    results = await asyncio.gather(*tasks)
    
    # 统计处理结果
    success_count = sum(results)
    print(f"\nProcess complete: {success_count}/{len(results)} files succeeded")
    return success_count, len(results)


def retry_run(file_paths):
    # 设置并发参数
    MAX_CONCURRENT = 100  
    # 根据系统资源调整
    success_count, total_count = asyncio.run(batch_process_files(file_paths, MAX_CONCURRENT))
    # 如果没跑完，等待一分钟后重试
    if(success_count < total_count):
        time.sleep(60)
        retry_run(file_paths)

if __name__ == "__main__":
    # 获取文件列表（示例目录）
    input_dir = Path('/Users/louisliu/dev/LLM/new')
    file_paths = list(input_dir.glob('*.md'))
    
    # 执行异步处理
    start = datetime.now()

    retry_run(file_paths)
    
    # 输出耗时
    duration = (datetime.now() - start).total_seconds()
    print(f"Total processing time: {duration:.2f} seconds")