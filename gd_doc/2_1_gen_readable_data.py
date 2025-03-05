
import os


def write_final_file(name, text):
    with open(f'/Users/louisliu/dev/LLM/final/{name}', 'w', encoding='utf-8') as f:
        f.write(text)

def llm_clean(text):

    from langchain_ollama import ChatOllama
    from langchain.callbacks.manager import CallbackManager
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

    # ollama模型

    llm = ChatOllama(
        base_url='https://c2bf-35-188-72-196.ngrok-free.app/',
        model="MFDoom/deepseek-r1-tool-calling:32b-qwen-distill-q4_K_M",
        temperature=0.1,
        callbacks=callback_manager
    )

    # llm = ChatOllama(
    #     base_url='http://localhost:11434',
    #     model="llama3.1:8b",
    #     temperature=0.7,
    #     callbacks=callback_manager
    # )

    # vllm
    from langchain_openai import ChatOpenAI

    # llm = ChatOpenAI(
    #     base_url='https://shannon1997-a0m85kaya8fn-8000.gear-c1.openbayes.net/v1/',
    #     model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    #     temperature=0.7,
    #     callbacks=callback_manager,
    #     api_key='123'
    # )

    # 千问max
    OPENAI_API_KEY = 'sk-8e793baf80dd423e92386c2486209666'

    llm = ChatOpenAI(model='qwen-max',
                api_key=OPENAI_API_KEY,
                base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                temperature=0, 
                callbacks=callback_manager)


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

    response = llm.invoke(system_message)
    
    return response.content


text = '''
    \n\n_2025年02月06日 16:01_ _海南_\n\n轻武器实弹射击的组织与实施教案\n\n  \n\n作业提要\n\n课目：轻武器实弹射击的组织与实施\n\n内容：1.场地设置\n\n\xa0 \xa0 \xa0 \xa0 \xa0 \xa02.组织流程\n\n\xa0 \xa0 \xa0 \xa0 \xa0 \xa03.安全保障\n\n目的：1.通过实弹射击训练，掌握瞄准、击发等基本射击要领。\n\n\xa0 \xa0 \xa0 \xa0 \xa0 2.培养参训人员严格遵守安全规程的意识，确保训练安全。\n\n方法：理论提示、讲解示范、组织练习、小结讲评。\n\n时间：xx分钟\n\n地点：射击训练场\n\n要求：1.严格武器操作规程，严禁枪口对人，以防事故发生。\n\n\xa0 \xa0 \xa0 \xa0 \xa0 2.积极开动脑筋，仔细体会动作要领，提高训练效果。\n\n器材保障：（略）\n\n\n\n  \n\n作业进程\n\n一、作业准备\\----------------------------xx分钟\n\n1.验枪，清点人数，整理着装，报告；\n\n2.宣布作业提要；\n\n3.提示有关理论。\n\n二、作业实施\\----------------------------xx分钟\n\n  \n\n\xa0 \xa0 \xa0 \xa0 第一个训练内容：轻武器实弹射击场地设置\n\n【理论提示】\n\n\xa0 \xa0场地设置是实弹射击顺利进行的重要保障，因此应严格按规定设置场地。场地一般按“三区三所二线一台一靶壕”进行设置。分别为：三区是待机区、射击区、集合区，三所是指挥所、弹药所、救护所，二线是射击出发地线、射击地线，一台是成绩记录台，一靶壕是报靶人员隐蔽们壕沟。\n\n【现地观摩】\n\n\n\n\xa0 \xa0同志们，以上我们组织了现地观摩，科学规范的场地设置是保障实弹射击安全顺利进行的前提，大家一定按要求设置好实弹投掷场地。\n\n【小结讲评】（略）\n\n  \n\n\xa0 第二个训练内容：轻武器实弹射击组织流程\n\n【理论提示】\n\n\xa0 轻武器实弹射击组织流程一般按照：人员编组、领取弹药器材、设置场地、进行动员、实弹射击、公布成绩、小结讲评的步骤进行。\n\n【讲解示范】\n\n（一）射击前准备  \n\n1\\. 设置场地\n\n\xa0 \xa0射击前按“三区三所二线一台一靶壕”进行设置场地，确认射击场符合安全标准（靶档高度、射界范围、安全区）。\n\n2\\. 领取武器、弹药和器材  \n\n\xa0 领取武器、弹药、靶子、报靶杆、安全显示旗等以及急救箱、灭火器等应急器材。\xa0\xa0\n\n3\\. 派出相关人员并明确职责\n\n\xa0 \xa0派出地线指挥员、发弹员、报靶员、记录员、安全员、卫生员并明确职责。\xa0\n\n【边讲边做】\xa0\xa0\xa0\n\n\xa0 （二）射击流程\n\n\xa0 1.领取武器弹药\n\n\xa0 组长带队至弹药所按规定领取武器弹药，并将子弹装入空弹匣内，然后装入子弹带内。\n\n\xa0 2.射击出发地线散开\n\n\xa0 听到地线指导员下达“xx组在射击出发地线散开”的口令后，依次对正自己的靶位在射击出发地线散开。  \n\n\xa0 3.向射击地线出发\n\n\xa0 \xa0听到地线指导员下达“xx组向射击地线出发”的口令后，依次对正自己的靶位在射击地线前进。到达射击地线后，自行对正自己相应的射击靶位。\n\n\xa0 \xa04.实弹射击\n\n\xa0 听到“卧姿装子弹”的口令后，迅速卧倒、装子弹、据枪、瞄准、射击。射击完毕听到“退子弹起立”的口令后按规定退子弹起立。，听指挥员口令验枪向组长靠拢。\n\n\xa0 5.验枪\n\n\xa0 听到指挥员下达“验枪”的口令，进行验枪，清点剩余弹药。\n\n\xa0 6.报靶\xa0\xa0\n\n\xa0 指导员下达向组长靠拢的口令，射击人员向1号靶位（组长）靠拢。指导员向报靶人员发出检靶的信号，报靶人员报靶，记录员登记成绩。\xa0\n\n\xa0 \xa07.公布成绩\n\n\xa0【组织练习】\xa0\xa0\n\n\xa0 \xa0下面我们进行体会练习（教练员检查纠正）；各班按场地划分带开，体会开始。停，在刚才的练习中，大家体会动作比较认真，但是动作还不确实，希望下步训练时注意。\n\n【小结讲评】（略）\n\n  \n\n\xa0第三个训练内容：轻武器实弹射击安全保障\n\n【理论讲解】\n\n\xa0 做好轻武器实弹射击安全工作非常重要。实弹射击前要进去专题教育，并明确相关规定，提出相应要求。\n\n\xa0 \xa0特别强调严格按武器操作规程，严禁枪口对人、严禁非指令装弹。严禁在实弹射击场地内超越警戒线、严禁私藏弹药等，要杜绝麻痹思想。\n\n\xa0【讨论发言】\xa0\xa0\n\n\xa0 \xa0同志们，在组织轻武器实弹射击时会遇到哪些不安全的问题大家进行发言。停，刚才发言比较主动也很热烈，大家思考了不少问题。下面我归纳一下。\n\n【归纳小结】\n\n\xa0 轻武器实弹射击可能遇到的问题：一是有思想顾虑；二是不按操作规程操作；三是不听信号和口令；四是子弹卡壳等。实际上，实弹射击中可能遇到的问题还很多，我们要提前预想，要有处置预案，并要进行反复训练，确实做到不打无准备之仗。\n\n作业讲评\n\n1.重述课目、内容、目的、方法及重点；\n\n2.评估训练效果，表扬好人好事；\n\n3.指出优缺点，明确努力方向，宣布下次训练内容。\n\n图源网络，版权属原作者，向原作者致谢。\n\n\n\n预览时标签不可点\n\n关闭\n\n更多\n\n名称已清空\n\n
'''
print(llm_clean(text=text))
exit(0)

os.makedirs('/Users/louisliu/dev/LLM/final', exist_ok=True)

for root, _, files in os.walk('/Users/louisliu/dev/LLM/new'):
    for file in files:
        file_path = os.path.join(root, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            print(f'\n\n{text}\n')
            new_text = llm_clean(text)
            print(f'\n{new_text}\n\n')
            write_final_file(file, new_text)
