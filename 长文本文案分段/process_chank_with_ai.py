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

# 将文章切分处理

# 全局设置是否流式处理
is_streaming = True

# 分段长度
chank_size = 2000
# 重叠长度
overlap = 0

# 初始化 ChatOpenAI 实例 (在函数外部)
OPENAI_API_KEY = 'hxkj2025'
llm = ChatOpenAI(model='deepseek',
            api_key=OPENAI_API_KEY,
            base_url='https://ai01.hpccube.com:65016/ai-forward/d90177765e5346e891bf019a18a16f3da0008080/v1',
            # base_url='https://ai111.hpccube.com:65062/ai-forward/83d4e0a0eee742e5a182cd43cae9dab9a0008000/v1',
            streaming=is_streaming,
            temperature=0,
            request_timeout=3600,
            max_retries=0
            )

# 切分文档为一个个chank列表
def split_content_to_chanks(content: str) -> list:
    import math
    chanks = []
    chunk_num = math.ceil(len(content) / (chank_size - overlap))
    assert chank_size > overlap, '重叠长度不能大于分段大小!'
    for i in range(0, chunk_num):
        start_index = i * chank_size - overlap if i > 0 else 0
        end_index = start_index + chank_size
        # 左闭右开，+1
        text = content[start_index : end_index + 1]
        chanks.append(text)
    return chanks
    

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
        # print(f"Sending streaming request: {prompt[:100]}...")
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
        response = await llm.ainvoke(prompt, stream=is_streaming)
        result = response.content
    except Exception as e:
        print(f"LLM request error: {e}")
    # response 将是一个异步生成器
    return result 

# 大模型清洗文本（获取文本段落及内容）
async def do_llm_clean(text, think_tag = 'think'):

    template  = '''
    你是一个文档结构化专家，请将提供的文档结构化为所描述的形式。
    直接获取原本文档中的内容进行结构化，每一段内容均以<####>隔开，不要自行添加其他内容。
    生成完毕后请反复检查，确认不要包含“目录”相关的结果返回。
    注意：
    - 标题只需要最多3级，内容会包含最多3级标题以下的所有下级标题及文本内容。
    - 每一个分段不要漏掉标题层级，如果当前是3级标题，那么1级和2级标题页要包含在内。
    

    以下是一个例子：
    结构化前：

    1总则
    1.1编制依据
    依据《中华人民共和国突发事件应对法》《国家突发事件总体应急预案》《北京市实施＜中华人民共和国突发事件应对法＞办法》《北京市突发事件总体应急预案》等有关法律法规文件，以及本区突发事件应对工作实际，制定本预案。
    1.2适用范围
    本预案主要用于指导预防和处置发生在昌平区行政区域内，或发生在其他地区涉及昌平区的，应由昌平区处置或参与处置的各类突发事件。
    本预案所称突发事件是指突然发生，造成或可能造成严重社会危害，需要采取应急处置措施予以应对的自然灾害、事故灾难、公共卫生事件和社会安全事件。
    1.3工作原则
    坚持人民至上、生命至上。提高防范意识，有效控制危机，力争实现早发现、早报告、早控制、早解决，将突发事件造成的损失减少到最低程度。
    1.4突发事件分类分级
    1.4.1本区突发事件主要包括以下类别:
    (1)自然灾害。
    (2)事故灾难。

    结构化后：
    标题：1.总则 1.1 编制依据
    内容：依据《中华人民共和国突发事件应对法》《国家突发事件总体应急预案》《北京市实施＜中华人民共和国突发事件应对法＞办法》《北京市突发事件总体应急预案》等有关法律法规文件，以及本区突发事件应对工作实际，制定本预案。
    <####>
    标题：1.总则 1.2 适用范围
    内容：本预案主要用于指导预防和处置发生在昌平区行政区域内，或发生在其他地区涉及昌平区的，应由昌平区处置或参与处置的各类突发事件。
    本预案所称突发事件是指突然发生，造成或可能造成严重社会危害，需要采取应急处置措施予以应对的自然灾害、事故灾难、公共卫生事件和社会安全事件。
    <####>
    标题：1.总则 1.3 工作原则
    内容：坚持人民至上、生命至上。提高防范意识，有效控制危机，力争实现早发现、早报告、早控制、早解决，将突发事件造成的损失减少到最低程度。
    <####>
    标题：1.总则 1.4 突发事件分类分级 1.4.1 本区突发事件主要包括以下类别:
    内容：(1)自然灾害。
    (2)事故灾难。

    要转换的文本如下：
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
            # 如果文件不存在，才进行处理。处理过的文件就不处理了
            if(not os.path.exists(dist_file_path)):
                content = await get_doc_content(file_path=file_path_str)
                # 文本不能太短，太短说明有问题，跳过
                if (len(content) > 100):
                    # 文章内容分段
                    chanks = split_content_to_chanks(content)
                    cleaned_chanks = []
                    for chank in chanks:
                        # 大模型处理文本信息
                        cleaned_chank = await do_llm_clean(chank)
                        cleaned_chanks.append(cleaned_chank)
                        print(f'分段:{cleaned_chank}')
                        print('*'*10)
                        
                    # 所有处理过的chank组合成字符串
                    processed_content = '\n'.join(cleaned_chanks)
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
    MAX_CONCURRENT = 1
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