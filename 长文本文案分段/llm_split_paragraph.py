# pip install python-docx pypandoc -i https://pypi.tuna.tsinghua.edu.cn/simple
import asyncio
from datetime import datetime
import os
import sys
import time
import aiofiles
from pathlib import Path
import docx
import pypandoc
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

'''
整个文档全部给到llm进行分段处理，流式处理
功能没问题，但一篇文章可能很长，需要大模型要有很大的上下文，费钱
'''

# 全局设置是否流式处理
is_streaming = True

# 初始化 ChatOpenAI 实例 (在函数外部)
OPENAI_API_KEY = 'hxkj2025'
llm = ChatOpenAI(model='deepseek',
            api_key=OPENAI_API_KEY,
            # base_url='https://ai01.hpccube.com:65016/ai-forward/d90177765e5346e891bf019a18a16f3da0009000/v1',
            base_url='https://ai111.hpccube.com:65062/ai-forward/83d4e0a0eee742e5a182cd43cae9dab9a0008000/v1',
            streaming=is_streaming,
            temperature=0,
            request_timeout=3600,
            max_retries=0
            )

# docx转txt
def convert_docx_to_text(file_path):
    """读取 .docx 文档并返回文本内容。"""
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"读取 .docx 文件 {file_path} 时发生错误: {e}")
        return None

# doc转txt
def convert_doc_to_text(file_path):
    """使用 pypandoc 将 .doc 文档转换为文本。"""
    try:
        output = pypandoc.convert_file(file_path, 'plain', outputfile=None)
        return output
    except Exception as e:
        print(f"转换 .doc 文件 {file_path} 时发生错误 (请确保安装了 pandoc): {e}")
        return None

# 提取文档内容
async def get_doc_content(file_path):
    """读取并返回文档的文本内容。"""
    text = ''
    if os.path.isfile(file_path):
        if file_path.endswith(".docx"):
            # 使用asyncio.to_thread转为异步处理
            text = await asyncio.to_thread(convert_docx_to_text, file_path)
        elif file_path.endswith(".doc"):
            # 使用asyncio.to_thread转为异步处理
            text = await asyncio.to_thread(convert_doc_to_text, file_path)
    return text

# 流式请求LLM
async def llm_data_process_streaming(prompt):
    response = ''
    try:
        # 打印请求消息，确保消息正确
        print(f"Sending streaming request: {prompt[:100]}...")  # 输出前100字符作为调试
        # 启用流式传输
        processed_chunks = llm.astream(prompt)
        async for chunk in processed_chunks:
            text = chunk.text()
            # 处理每个数据块 (chunk)
            response += text
            # # 清空当前行并打印新的内容
            # print(text, end='', flush=True)  # 在同一行打印内容并刷新
            # sys.stdout.flush() 
            
    except Exception as e:
        print(f"LLM request error: {e}")
    # response 将是一个异步生成器
    return response

# 非流式请求LLM
async def llm_data_process(prompt):
    try:
        # 打印请求消息，确保消息正确
        print(f"Sending request: {prompt[:100]}...")  # 输出前100字符作为调试
        # 启用流式传输
        response = await llm.ainvoke(prompt)
        result = response.content
    except Exception as e:
        print(f"LLM request error: {e}")
    # response 将是一个异步生成器
    return result 

# 大模型清洗文本（获取文本段落及内容）
async def do_llm_clean(text, think_tag = 'think'):

    template  = '''
    你是一个文档结构化专家，请将提供的文档内容结构化为以下格式的 JSON 数组：

    每个文档部分应该按以下规则输出：
    - 结构化后的内容用 JSON 对象表示，每个对象包含两个字段：
    - `input` 字段，表示文档的标题或编号（如：1总则、2细则等）。
    - `output` 字段，表示与该标题相关的详细内容，所有内容保持原格式，并确保换行符 `\n` 不丢失。
    
    以下是一个例子：
    结构化前：

    示例输入：
    1总则
    1.1编制依据
    编制依据内容
    1.2适用范围
    适用范围内容
    1.3工作原则
    工作原则内容
    1.4突发事件分类分级
    1.4.1本区突发事件主要包括以下类别:
    (1)自然灾害。
    (2)事故灾难。
    2细则
    2.1细则1
    细则1内容

    期望的输出：
    [
        {{
            "input": "总则", 
            "output": "1总则\n1.1编制依据\n编制依据内容\n1.2适用范围\n适用范围内容\n1.3工作原则\n工作原则内容\n1.4突发事件分类分级\n1.4.1本区突发事件主要包括以下类别:\n(1)自然灾害。\n(2)事故灾难。"
        }},
        {{
            "input": "细则",
            "output": "2.1细则1\n细则1内容"
        }}
    ]

    请确保文档内容与结构化后的 JSON 输出严格一致，且不要包含任何关于“目录”或“附录”的内容。

    输入文档内容如下：
    {text}
    '''

    result = ''
    prompt = PromptTemplate.from_template(template) 
    system_message = prompt.format(text=text)
    # 流式处理
    if is_streaming:
        result  = await llm_data_process_streaming(system_message)
    # 非流式处理
    else:
        result = await llm_data_process(system_message)
    # 去掉思考标签
    if result.find(f'</{think_tag}>') > -1:
        result = result.split(f'</{think_tag}>')[-1]
    return result

# 提取文章每段落信息，存到目标目录下
# is_streaming  是否流式处理
async def process_file(file_path, semaphore, is_streaming=True):
    dist_path = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/dist'
    # 文件名
    file_name = f'{file_path.stem}.txt'
    dist_file_path = os.path.join(dist_path, file_name)
    file_path_str = str(file_path)
    """
    异步处理单个文件
    :param file_path: 文件路径
    :param semaphore: 并发控制信号量
    """
    async with semaphore:  # 限制并发量
        print(f"Task {file_path.name} acquired semaphore (value: {semaphore._value})")
        try:
            content = await get_doc_content(file_path=file_path_str)
            # 如果文件不存在，才进行处理。处理过的文件就不处理了
            if(not os.path.exists(dist_file_path)):
                # 大模型处理文本信息
                # 文本不能太短，太短说明有问题，跳过
                if (len(content) > 100):
                    # content = content[:100]
                    processed_content = await do_llm_clean(content)
                    if len(processed_content) > 100:
                        async with aiofiles.open(dist_file_path, 'w', encoding='utf-8') as f:
                            await f.write(processed_content)
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return False

# 批量处理文档
async def batch_process_files(file_paths, max_concurrency=10):
    """
    批量处理文件
    :param file_paths: 文件路径列表
    :param max_concurrency: 最大并发数
    """
    # 创建输出目录
    Path('长文本文案分段/dist').mkdir(exist_ok=True)
    
    # 使用信号量控制并发量
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # 创建并执行所有任务
    tasks = [process_file(fp, semaphore, is_streaming) for fp in file_paths]
    results = await asyncio.gather(*tasks)
    
    # 统计处理结果
    success_count = sum(results)
    print(f"\n已经处理: {success_count}/{len(results)} 文件")
    return success_count, len(results)

# 启动执行任务 支持重试
def retry_run(file_paths):
    # 设置并发参数
    MAX_CONCURRENT = 2
    # 根据系统资源调整
    success_count, total_count = asyncio.run(batch_process_files(file_paths, MAX_CONCURRENT))    
    # # 如果没跑完，等待一分钟后重试
    # if(success_count < total_count):
    #     time.sleep(60)
    #     retry_run(file_paths)

if __name__ == "__main__":
    input_dir = "/Users/louisliu/dev/LLM/知识库/北京市/昌平区"
    path = Path(input_dir)
    # 获取所有后缀名文件路径列表
    all_files = list(path.rglob('*.doc'))
    doc_files = list(path.rglob('*.docx'))
    all_files.extend(doc_files)

    start = datetime.now()

    retry_run(all_files)
    
    # 输出耗时
    duration = (datetime.now() - start).total_seconds()
    print(f"处理时间: {duration:.2f} 秒")