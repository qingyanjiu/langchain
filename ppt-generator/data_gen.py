import re
from langchain.chat_models.openai import ChatOpenAI

# 创建 ChatOpenAI 实例
llm = ChatOpenAI(model_name="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", 
                        temperature=0.7, 
                        api_key='sk-sdcxstsuwiefzutgkridojrlcovgaggxddyvaicqwynpxebq', 
                        base_url='https://api.siliconflow.cn/v1')

def extract_items(input_string):
    # 查找 << >> 内的内容
    content = re.search(r'<<(.+?)>>', input_string.content)
    if content:
        content = content.group(1)
    else:
        return []
    
    # 按 | 分割内容并去除空格
    items = [item.strip() for item in content.split('|')]
    
    # 去除引号
    items = [re.sub(r'^"|"$', '', item) for item in items]
    
    return items

def slide_data_gen(topic, page_num=5):
    slide_data = []
    point_count = 5

    slide_data.append(extract_items(llm.invoke(f"""
    你是一个擅长文本总结和格式化的模型，能够提取相关信息。
    
    针对主题 "{topic}"，请建议一个演示文稿的标题和副标题，返回格式如下：
    << "标题" | "副标题" >>
    
    示例：
    << "设计原则" | "将原则整合到设计流程中" >>
    """)))

    slide_data.append(extract_items(llm.invoke(f"""
    你是一个擅长文本总结和格式化的模型，能够提取相关信息。
    
    针对主题 "{topic}"，演示文稿标题为 "{slide_data[0][0]}"，副标题为 "{slide_data[0][1]}"，
    请编写 {page_num} 张幻灯片的目录，每张幻灯片对应一个小标题。
    结果格式如下：
    << "幻灯片1" | "幻灯片2" | "幻灯片3" | ... | >>
    
    示例：
    << "设计伦理简介" | "以用户为中心的设计" | "透明度与诚信" | "数据隐私与安全" | "无障碍设计与包容性" | "社会影响与可持续性" | "人工智能伦理" >>
    """)))

    for subtopic in slide_data[1]:
        data_to_clean = llm.invoke(f"""
        你是一个擅长内容生成的模型，能够提取相关信息并以清晰简洁的方式呈现。
        
        针对主题 "{topic}"，演示文稿标题为 "{slide_data[0][0]}"，副标题为 "{slide_data[0][1]}"，
        请撰写一张关于 "{subtopic}" 的幻灯片内容。
        
        请写出 {point_count} 个要点，每个要点最多 10 个字。
        要点应简短、清晰、直奔主题。
        """)

        cleaned_data = llm.invoke(f"""
        你是一个擅长文本总结和格式化的模型，能够提取相关信息并按用户指定的格式呈现。
        
        以下是一张幻灯片的文本草稿，包含 {point_count} 个要点，请提取 {point_count} 句话，并按以下格式返回：
        
        << "要点1" | "要点2" | "要点3" | ... | >>
        
        示例：
        << "营造合作和包容的工作环境。" | "尊重知识产权，避免抄袭。" | "遵守专业标准和伦理准则。" | "开放接受反馈，持续学习。" >>
        
        -- 文本开始 --
        {data_to_clean}
        -- 文本结束 --
        """)

        slide_data.append([subtopic] + extract_items(cleaned_data))

    return slide_data