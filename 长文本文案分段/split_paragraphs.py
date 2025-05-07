import os
from pathlib import Path
import re
import docx
import pypandoc

dist_path = '/Users/louisliu/dev/AI_projects/langchain/长文本文案分段/split'
para_max_size = 20

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
    return text

# 使用正则按照段落标题切分正片文章
def do_split(all_files):
    for file_path in all_files:
        file_name_raw = file_path.stem
        file_name = f'{file_path.stem}.txt'
        dist_file_path = os.path.join(dist_path, file_name)
        file_path_str = str(file_path)
        content = get_doc_content(file_path_str)

        # 正则匹配一级标题
        regex_lv1 = r"\n\d{1,2}\s*[\u4e00-\u9fa5（）]*\n"

        all_para_list = []
        lv1_para_list = split_para(content, regex_lv1)

        for para_lv1 in lv1_para_list:
            # 提取标题
            title_lv1 = para_lv1.split('\n')[1]
            para_lv1 = para_lv1.split(title_lv1)[-1]
            full_title = f'{file_name_raw}-{title_lv1}\n------'
            
            # 切分二级标题
            if len(para_lv1) > para_max_size:
                # 正则匹配2级标题
                regex_lv2 = r"\n\d{1,2}.\d{1,2}\s*[\u4e00-\u9fa5（）]*\n"
                lv2_para_list = split_para(para_lv1, regex_lv2)
                for para_lv2 in lv2_para_list:
                    # 提取标题
                    title_lv2 = para_lv2.split('\n')[1]
                    para_lv2 = para_lv2.split(title_lv2)[-1]
                    full_title = f'{file_name_raw}-{title_lv1}-{title_lv2}\n------'
                    
                    # 切分三级标题
                    if len(para_lv2) > para_max_size:
                        # 正则匹配3级标题
                        regex_lv3 = r"\n\d{1,2}.d{1,2}.\d{1,2}\s*[\u4e00-\u9fa5（）]*\n"
                        lv3_para_list = split_para(para_lv2, regex_lv3)
                        # 每一项前面加上title
                        lv3_para_list = list(map(lambda x: f'{full_title}-{x}', lv3_para_list))
                        if len(lv3_para_list) > 0:
                            lv3_splited_content = '<*** DIVIDER ***>\n'.join(lv3_para_list)
                            all_para_list.append(lv3_splited_content)
                        else:
                            all_para_list.append(f'{full_title}{para_lv2}')
                    else:
                        all_para_list.append(f'{full_title}{para_lv2}')
            
            else:
                all_para_list.append(f'{full_title}{para_lv1}')

        splited_content = '<*** DIVIDER ***>\n'.join(all_para_list)
        # 替换掉重复的分隔符
        splited_content = splited_content.replace('<*** DIVIDER ***>\n<*** DIVIDER ***>', '<*** DIVIDER ***>')

		# 写文件
        with open(dist_file_path, 'w', encoding='utf-8') as f:
            f.write(splited_content)

def split_para(content, regex):
    para_list = []
    # 每一段开始的下标
    para_start_index_list = []
	# 匹配进行分段
    matches = re.finditer(regex, content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
		# print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
        para_start_index_list.append(match.start())

	# 有多少段
    para_num = len(para_start_index_list)
    for idx in range(0, para_num):
		# 切分每一段
        if idx < para_num - 1:
            para_content = content[para_start_index_list[idx]:para_start_index_list[idx + 1] + 1]
		# 如果是最后一段
        else:
            para_content = content[para_start_index_list[idx]:]
        para_list.append(para_content)
    return para_list
    

if __name__ == "__main__":
	input_dir = "/Users/louisliu/dev/LLM/知识库/北京市/昌平区"
	path = Path(input_dir)
	# 获取所有后缀名文件路径列表
	all_files = list(path.rglob('*.doc'))
	doc_files = list(path.rglob('*.docx'))
	all_files.extend(doc_files)
	do_split(all_files)