# pip install lanchain==0.3.19 langchain-openai==0.3.7 -i https://pypi.tuna.tsinghua.edu.cn/simple
import asyncio
import os
from pathlib import Path
import re
import shutil
import subprocess
import docx
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import pypandoc
import json

'''
通过正则表达式分段，然后用llm处理input
对于固定标题的文档来说，这种方式效率最高，分段后上下文变少了，交给大模型处理也比较合理
'''

# 初始化 ChatOpenAI 实例 (在函数外部)
OPENAI_API_KEY = 'hxkj2025'
llm = ChatOpenAI(model='deepseek',
            api_key=OPENAI_API_KEY,
            # base_url='https://ai01.hpccube.com:65016/ai-forward/d90177765e5346e891bf019a18a16f3da0009000/v1',
            base_url='https://ai111.hpccube.com:65062/ai-forward/83d4e0a0eee742e5a182cd43cae9dab9a0008000/v1',
            streaming=True,
            temperature=0,
            request_timeout=120,
            max_retries=0
            )

split_path_str = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/split'
PARA_MAX_SIZE = 20

MAIN_DIVIDER = '<*** DIVIDER ***>'
SUB_DIVIDER = '\n------\n'

# 大模型批量处理的并行线程数
MAX_LLM_PROCESS_SEMAPHORE = 10

# 目录过滤，长度不够这个数认为是目录，删掉
INDEX_LEN_LIMIT = 100

# 一共有多少数据
total_count = 0
# 已经处理了多少条数据
processed_count = 0

''' 
第一种标题分割格式正则（共分割三级标题）
1 xx or 1.xx
1.1 xx
1.1.1 xx
'''
title_regex_1 = [
    r"\n\d{1,2}[\.\s]*[\u4e00-\u9fa5（）]*?\n", 
    r"\n\d{1,2}\.\d{1,2}\s*[\u4e00-\u9fa5（）]*?\n", 
    r"\n\d{1,2}\.\d{1,2}\.\d{1,2}\s*.*?[。\n]"
]
''' 
第二种标题分割格式正则（共分割三级标题）
一、 xx or 一 xx
（一）xx
1.xx or 1 xx
'''
title_regex_2 = [
    r'\n[一二三四五六七八九十][\.\s、]*[\u4e00-\u9fa5（）]*.*?\n', 
    r'\n（[一二三四五六七八九十]）[\.\s、]*[\u4e00-\u9fa5（）]*.*?\n', 
    r'\n\d{1,2}[\.\s]*[\u4e00-\u9fa5（）]*.*?[。；\n]'
]

# 通过大模型用给定的实例文本内容生成思考内容（也就是让大模型去分析一下这段文字怎么写最合适，要注意哪些点。这个内容最后放到think里去训练）
async def llm_gen_think_content(data, tmp_save_obj, semaphore):
    global processed_count
    template = '''
        你是一个方案写作专家，很擅长分析方案中段落内部的逻辑。
        以下是一篇名为《{title}》下名为“{para_title}”段落的内容，请分析一下该段落内容写作时要注意的点，给出指导意见，说明如何才能写好本段落的内容。
        请注意：直接返回指导意见，不要包含其他描述性的内容。
        
        段落内容如下：
        {text}
    '''
    prompt = PromptTemplate.from_template(template) 
    async with semaphore:
        meessage = prompt.format(text=data['output'], title=data['title'], para_title=data['input'])
        response = await llm.ainvoke(meessage)
        resp = response.content
        resp = resp.split('</think>')[-1]
        # 替换input
        data['think'] = resp
        tmp_save_obj.append(data)
        processed_count += 1
        print(f'***** 累计已处理 {processed_count} 条数据 *****')
        

# async def llm_replace_input(data, tmp_save_obj, semaphore):
#     template = '''
#         你是一个经验丰富的文案工作者，现在需要将一些方案的标题和段落信息进行重新编辑，以下是一些例子：
        
#         例子1：
#         原内容：太原市交通运输突发事件应急预案-1.总则-1.3 工作原则
#         编辑后内容： 请为《太原市交通运输突发事件应急预案》编写其中某个段落的内容。段落的标题是“工作原则”，主要描述的是"方案总则"中工作原则的相关内容。
        
#         例子2：
#         原内容：太原市安全生产事故灾难应急预案-6保障措施-6.5奖励与责任追究-6.5.2责任追究
#         编辑后内容： 请为《太原市安全生产事故灾难应急预案》编写其中某个段落的内容。段落的标题是“责任追究”，主要描述的是"保障措施"中"奖励与责任追究"中工作原则的相关内容。
        
#         例子3：
#         原内容：河北省城市排水防涝应急预案-二、组织指挥体系及职责-（一）省住房城乡建设厅组织指挥体系-2.工作职责
#         编辑后内容： 请为《河北省城市排水防涝应急预案》编写其中某个段落的内容。段落的标题是“工作职责”，主要描述的是"组织指挥体系及职责"中"省住房城乡建设厅组织指挥体系"中工作职责的相关内容。

#         需要编辑的内容: 
#         {text}
        
#         请注意：返回的结果中不要包含“编辑后内容”这种文字，直接返回结果即可。
#     '''
#     prompt = PromptTemplate.from_template(template) 
#     async with semaphore:
#         meessage = prompt.format(text=data['input'])
#         response = await llm.ainvoke(meessage)
#         resp = response.content
#         resp = resp.split('</think>')[-1]
#         # 替换input
#         data['input'] = resp
#         tmp_save_obj.append(data)
            

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
def get_doc_content(file_path):
    """读取并返回文档的文本内容。"""
    text = ''
    if os.path.isfile(file_path):
        if file_path.endswith(".docx"):
            # 使用asyncio.to_thread转为异步处理
            text = convert_docx_to_text(file_path)
        elif file_path.endswith(".doc"):
            # 使用asyncio.to_thread转为异步处理
            text = convert_doc_to_text(file_path)
        elif file_path.endswith(".txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    return text

# 使用正则按照段落标题切分正片文章
def do_split(all_files, lv_1_3_regex):
    split_path = Path(split_path_str)
    # 先创建目录
    split_path.mkdir(parents=True, exist_ok=True)
    
    for file_path in all_files:
        # 文档标题（不带后缀）
        file_name_raw = file_path.stem
        # 删除标题中的特殊内容
        # 开头的1- 2-
        file_name_raw = re.sub(r'^\d+-', '', file_name_raw)
        # 全角括号及中间字符
        file_name_raw = re.sub(r'（.*）', '', file_name_raw)
        # 半角括号及中间字符
        file_name_raw = re.sub(r'\(.*\)', '', file_name_raw)
        # 空格
        file_name_raw = re.sub(r' ', '', file_name_raw)
        
        file_name = f'{file_path.stem}.txt'
        dist_file_path = os.path.join(split_path_str, file_name)
        file_path_str = str(file_path)
        content = get_doc_content(file_path_str)
        
        if not content:
            continue
        # 删除空格等字符
        content = content.replace("\ue004", "")\
            .replace("\ue010",'')\
            .replace("\u3000",'')\
            .replace("\u2003",'')\
            .replace('．', '.')\
            .replace('：', '')
        # 删除附件内容
        fj_regex = r"\n.*附件"
        fj_matches = re.finditer(fj_regex, content, re.MULTILINE)
        try:
            first_match = next(fj_matches)
            if first_match:
                start_idx = first_match.start()
                content = content[:start_idx + 1]
        except StopIteration:
            print(f'{file_name_raw} 中没有附件内容')
            
        # 正则匹配一级标题
        regex_lv1 = lv_1_3_regex[0]

        all_para_list = []
        lv1_para_list = split_para(content, regex_lv1)

        for para_lv1 in lv1_para_list:
            if len(para_lv1['content'].replace('\n', '')) < INDEX_LEN_LIMIT:
                continue
            # 提取标题
            title_lv1 = para_lv1['title']
            para_lv1 = para_lv1['content'].replace(para_lv1['title'], '')
            full_title = f'{file_name_raw}|{title_lv1}{SUB_DIVIDER}'
            
            # 切分二级标题
            if len(para_lv1) > PARA_MAX_SIZE:
                # 正则匹配2级标题
                regex_lv2 = lv_1_3_regex[1]
                lv2_para_list = split_para(para_lv1, regex_lv2)
                for para_lv2 in lv2_para_list:
                    # 提取标题
                    title_lv2 = para_lv2['title']
                    para_lv2 = para_lv2['content'].replace(para_lv2['title'], '')
                    full_title = f'{file_name_raw}|{title_lv1}-{title_lv2}{SUB_DIVIDER}'
                    
                    # 切分三级标题
                    if len(para_lv2) > PARA_MAX_SIZE:
                        # 正则匹配3级标题
                        regex_lv3 = lv_1_3_regex[2]
                        lv3_para_list = split_para(para_lv2, regex_lv3)
                        # 如果没有识别到三级的内容，直接二级内容拼上
                        if len(lv3_para_list) == 0:
                            all_para_list.append(f'{full_title}{para_lv2}')
                        else:    
                            for para_lv3 in lv3_para_list:
                                # 提取标题
                                title_lv3 = para_lv3['title']
                                para_lv3 = para_lv3['content'].replace(para_lv3['title'], '')
                                full_title = f'{file_name_raw}|{title_lv1}-{title_lv2}-{title_lv3}{SUB_DIVIDER}'
                            
                                lv3_content = f'{MAIN_DIVIDER}\n{full_title}{para_lv3}'
                                all_para_list.append(lv3_content)
                    else:
                        all_para_list.append(f'{full_title}{para_lv2}')
            
            else:
                all_para_list.append(f'{full_title}{para_lv1}')

        splited_content = f'{MAIN_DIVIDER}\n'.join(all_para_list)
        # 替换掉重复的分隔符
        splited_content = splited_content.replace(f'{MAIN_DIVIDER}\n{MAIN_DIVIDER}', MAIN_DIVIDER)

        if not splited_content:
            continue
            
		# 写文件
        with open(dist_file_path, 'w', encoding='utf-8') as f:
            f.write(splited_content)

# 分段
def split_para(content, regex):
    para_list = []
    # 每一段开始的下标
    para_start_index_list = []
    # 每一段匹配到的内容
    para_match_text = []
	# 匹配进行分段
    matches = re.finditer(regex, content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
		# print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
        para_start_index_list.append(match.start())
        para_match_text.append(match.group().replace('\n', ''))

	# 有多少段
    para_num = len(para_start_index_list)
    for idx in range(0, para_num):
		# 切分每一段
        if idx < para_num - 1:
            para_content = content[para_start_index_list[idx]:para_start_index_list[idx + 1] + 1]
		# 如果是最后一段
        else:
            para_content = content[para_start_index_list[idx]:]
        para_list.append({"content": para_content, "title": para_match_text[idx]})
    return para_list

# 切割完的文件段落转为json
def split_data_to_json(split_data_path):
    path = Path(split_data_path)
    files = list(path.rglob('*.txt'))
    result = []
    for file in files:
        with open(str(file), 'r', encoding='utf-8') as f:
            paras = f.read().split(MAIN_DIVIDER)
            for p in paras:
                if p:
                    title = p.split(SUB_DIVIDER)[0]
                    # 段落标题
                    para_title = title.split('|')[1].replace('\n', '')
                    # 文档标题
                    title = title.split('|')[0].replace('\n', '')
                    content = p.split(SUB_DIVIDER)[1]
                    # 判断下长度，大体上把目录内容过滤掉
                    if len(content) > INDEX_LEN_LIMIT:
                        content = content.replace('\n', '')
                        data_item = {"title": title, "input": para_title, "output": content}
                        result.append(data_item)
    return result

# 异步并行处理数据
async def do_llm_replace_title(json_object, tmp_save_obj):
    semaphore = asyncio.Semaphore(MAX_LLM_PROCESS_SEMAPHORE)
    tasks = []
    for j in json_object:
        task = asyncio.create_task(llm_gen_think_content(j, tmp_save_obj, semaphore))
        tasks.append(task)
    await asyncio.gather(*tasks)

# java将doc转为txt
def process_file_with_java(all_files, jar_path, doc_path_str, txt_path_str):
    ########### 预处理文件列表 #############
    # 文件复制到某个目录下
    for file in all_files:
        dist_path_str = os.path.join(doc_path_str, f'{file.name}')
        shutil.copy2(str(file), dist_path_str)
        
    # java 去将 RAG_DOC_DIST 目录下doc转为 txt 放到 RAG_DOC_DIST_TXT下
    args = [doc_path_str, txt_path_str]
    command = [
        'java',
        '-jar',
        jar_path,
        *args
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=True)
    print(process.stderr)

# 使用大模型处理分段后生成的json文件中的部分内容
def post_process_with_llm(json_object_to_save):
    global processed_count
    # 暂存的obj，防止中途出错数据全丢，暂时记录处理完的数据，如果报错，就写这个数据
    tmp_save_obj = []
    
    print(f'共 {len(json_object_to_save)} 条数据')
    
    # 找临时存储的文件，如果存在，则读取其中内容，过滤掉已经有的数据
    if os.path.exists('data-tmp.json'):
        with open('data-tmp.json', 'r', encoding='utf-8') as json_file:
            tmp_save_obj = json.loads(json_file.read())
        # 已处理的条数
        processed_count = len(tmp_save_obj)
        # 未暂存的数据列表，也就是要继续处理的数据，从已处理的条数下标开始往后继续处理
        json_object_to_save = json_object_to_save[processed_count:]
        print(f'临时存储文件存在，读取数据，继续处理剩余数据, 剩余 {len(json_object_to_save)} 条')
    else:
        print(f'临时存储文件不存在，处理所有数据')
    
    # 通过LLM并发处理input格式
    try:
        asyncio.run(do_llm_replace_title(json_object_to_save, tmp_save_obj))
    except Exception as e:
        # 如果抛异常，则写入临时数据文件
        if len(tmp_save_obj) > 0:
            print(f"发生错误: {e} 暂存已处理的 {len(tmp_save_obj)} 条数据")
            with open('data-tmp.json', 'w', encoding='utf-8') as json_file:
                json_file.write(json.dumps(tmp_save_obj, ensure_ascii=False))
            
    # 如果有暂存的数据，和处理好的数据一起写入
    if len(tmp_save_obj) > 0: 
        json_object_to_save = tmp_save_obj.extend(json_object_to_save)


if __name__ == "__main__":
    
    input_dir = "/Users/louisliu/dev/LLM/知识库"
    path = Path(input_dir)
    # 获取所有后缀名文件路径列表
    all_files = list(path.rglob('*.doc'))
    doc_files = list(path.rglob('*.docx'))
    all_files.extend(doc_files)
    
    # 文档目录，将提取到的文档放到这个目录下，供java去处理
    doc_path_str = '/Users/louisliu/dev/LLM/RAG_DOC_DIST'
    # java提取后的txt存到这里
    txt_path_str = '/Users/louisliu/dev/LLM/RAG_DOC_DIST_TXT'
    # jar包路径
    jar_path = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/jar/doc2txt.jar'
    
    # java提取doc内容，转为txt保存
    # process_file_with_java(all_files, jar_path, doc_path_str, txt_path_str)
    
    txt_path = Path(txt_path_str)
    txt_files = list(txt_path.rglob('*.txt'))
    # 使用两套不同的标题正则，处理转好的txt文件 
    # do_split(txt_files, title_regex_1)
    # do_split(txt_files, title_regex_2)
    
    # 生成json数据文件
    json_object_to_save = split_data_to_json(split_path_str)
    
    # 使用大模型处理分段后生成的json文件中的部分内容
    post_process_with_llm(json_object_to_save)
    
    with open('data.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(json_object_to_save, ensure_ascii=False, indent=2))
    
    # 处理完成，将tmp文件也更新成完整json，防止再点击运行的时候，又从上次跑到一半的地方开始
    with open('data-tmp.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(json_object_to_save, ensure_ascii=False, indent=2))
    
    print('处理完成')