import os
from pathlib import Path
import re
import shutil
import subprocess
import docx
from langchain_openai import ChatOpenAI
import pypandoc
import json

# 初始化 ChatOpenAI 实例 (在函数外部)
OPENAI_API_KEY = 'hxkj2025'
# llm = ChatOpenAI(model='deepseek',
#             api_key=OPENAI_API_KEY,
#             base_url='https://ai01.hpccube.com:65016/ai-forward/d90177765e5346e891bf019a18a16f3da0009000/v1',
#             # base_url='https://ai111.hpccube.com:65062/ai-forward/83d4e0a0eee742e5a182cd43cae9dab9a0008000/v1',
#             streaming=True,
#             temperature=0,
#             request_timeout=360,
#             max_retries=0
#             )

split_path_str = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/split'
para_max_size = 20

MAIN_DIVIDER = '<*** DIVIDER ***>'
SUB_DIVIDER = '\n------\n'

''' 
第一种标题分割格式正则（共分割三级标题）
1 xx or 1.xx
1.1 xx
1.1.1 xx
'''
title_regex_1 = [
    r"\n\d{1,2}[\.\s]*[\u4e00-\u9fa5（）]*.*?\n", 
    r"\n\d{1,2}\.\d{1,2}\s*[\u4e00-\u9fa5（）]*.*?\n", 
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

def llm_gen_input(text):
    template = '''
        你是一个经验丰富的文案工作者，现在需要将一些方案的标题和段落信息进行重新编辑，以下是一些例子：
        
        例子1：
        原内容：太原市交通运输突发事件应急预案-1.总则-1.3 工作原则
        编辑后内容： 请为《太原市交通运输突发事件应急预案》编写其中某个段落的内容。段落的标题是“工作原则”，主要描述的是"方案总则"中工作原则的相关内容。
        
        例子2：
        原内容：太原市安全生产事故灾难应急预案-6保障措施-6.5奖励与责任追究-6.5.2责任追究
        编辑后内容： 请为《太原市安全生产事故灾难应急预案》编写其中某个段落的内容。段落的标题是“责任追究”，主要描述的是"保障措施"中"奖励与责任追究"中工作原则的相关内容。
        
        例子3：
        原内容：太原市安全生产事故灾难应急预案-6保障措施-6.5奖励与责任追究-6.5.2责任追究
        编辑后内容： 请为《太原市安全生产事故灾难应急预案》编写其中某个段落的内容。段落的标题是“责任追究”，主要描述的是"保障措施"中"奖励与责任追究"中工作原则的相关内容。
        
    '''

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
            .replace('．', '.')\
            .replace('：', '')

        # 正则匹配一级标题
        regex_lv1 = lv_1_3_regex[0]

        all_para_list = []
        lv1_para_list = split_para(content, regex_lv1)

        for para_lv1 in lv1_para_list:
            if len(para_lv1['content']) < 200:
                continue
            # 提取标题
            title_lv1 = para_lv1['title']
            para_lv1 = para_lv1['content'].replace(para_lv1['title'], '')
            full_title = f'{file_name_raw}-{title_lv1}{SUB_DIVIDER}'
            
            # 切分二级标题
            if len(para_lv1) > para_max_size:
                # 正则匹配2级标题
                regex_lv2 = lv_1_3_regex[1]
                lv2_para_list = split_para(para_lv1, regex_lv2)
                for para_lv2 in lv2_para_list:
                    # 提取标题
                    title_lv2 = para_lv2['title']
                    para_lv2 = para_lv2['content'].replace(para_lv2['title'], '')
                    full_title = f'{file_name_raw}-{title_lv1}-{title_lv2}{SUB_DIVIDER}'
                    
                    # 切分三级标题
                    if len(para_lv2) > para_max_size:
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
                                full_title = f'{file_name_raw}-{title_lv1}-{title_lv2}-{title_lv3}{SUB_DIVIDER}'
                            
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
                    content = p.split(SUB_DIVIDER)[1]
                    if len(content) > 10:
                        content = content.replace('\n', '')
                        data_item = {"input": title, "output": content}
                        result.append(data_item)
    with open('data.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(result, ensure_ascii=False)) 

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
    
    ########### 预处理文件列表 #############
    ## 文件复制到某个目录下
    # for file in all_files:
    #     dist_path_str = os.path.join(doc_path_str, f'{file.name}')
    #     shutil.copy2(str(file), dist_path_str)
        
    # # java 去将 RAG_DOC_DIST 目录下doc转为 txt 放到 RAG_DOC_DIST_TXT下
    # jar_path = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/jar/doc2txt.jar'
    # args = [doc_path_str, txt_path_str]
    # command = [
    #     'java',
    #     '-jar',
    #     jar_path,
    #     *args
    # ]
    # process = subprocess.run(command, capture_output=True, text=True, check=True)
    # print(process.stderr)
    ########### 预处理文件列表 #############
    
    txt_path = Path(txt_path_str)
    txt_files = list(txt_path.rglob('*.txt'))
    # 使用两套不同的标题正则，处理转好的txt文件 
    do_split(txt_files, title_regex_1)
    do_split(txt_files, title_regex_2)
    
    # 生成json数据文件
    split_data_to_json(split_path_str)
    