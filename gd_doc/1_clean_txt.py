import os
import re

os.makedirs('/Users/louisliu/dev/LLM/new', exist_ok=True)

def write_new_file(name, text):
    with open(f'/Users/louisliu/dev/LLM/new/{name}', 'w', encoding='utf-8') as f:
        f.write(text)

for root, _, files in os.walk('/Users/louisliu/dev/LLM/mdContent'):
    for file in files:
        file_path = os.path.join(root, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                final_text = None
                text = f.read()
                if (file.find('东方红智库') != -1):
                    if (text.find('[东方红智库](javascript:void(0);)') != -1):
                        final_text = text[text.find('[东方红智库](javascript:void(0);)') + len('[东方红智库](javascript:void(0);)'): text.find('喜欢请关注我们哦 ！')]
                elif (file.find('军桥网') != -1):
                    if (text.find('[军桥网](javascript:void(0);)') != -1):
                        final_text = text[text.find('[军桥网](javascript:void(0);)') + len('[军桥网](javascript:void(0);)'): text.find('**微信扫一扫赞赏作者**')]
                elif (file.find('南京G_F_D_Y') != -1):
                    if (text.find('[南京G_F_D_Y](javascript:void(0);)') != -1):
                        final_text = text[text.find('[南京G_F_D_Y](javascript:void(0);)') + len('[南京G_F_D_Y](javascript:void(0);)'): text.find('你的赞和在看，我都喜欢')]
                elif (file.find('人防之声') != -1):
                    if (text.find('[人防之声](javascript:void(0);)') != -1):
                        final_text = text[text.find('[人防之声](javascript:void(0);)') + len('[人防之声](javascript:void(0);)'): text.find('**微信扫一扫赞赏作者**')]
                elif (file.find('知远战略与防务研究所') != -1):
                    if (text.find('[知远战略与防务研究所](javascript:void(0);)') != -1):
                        final_text = text[text.find('[知远战略与防务研究所](javascript:void(0);)') + len('[知远战略与防务研究所](javascript:void(0);)'): text.find('**微信扫一扫赞赏作者**')]
                elif (file.find('铸魂砺剑') != -1):
                    if (text.find('[铸魂砺剑](javascript:void(0);)') != -1):
                        final_text = text[text.find('[铸魂砺剑](javascript:void(0);)') + len('[铸魂砺剑](javascript:void(0);)'): text.find('**微信扫一扫赞赏作者**')]
                else:
                    pass


                if final_text:
                    final_text = re.sub(r'!\[.*?\]\([^\u4e00-\u9fff\u3400-\u4dbf]*\)', '', final_text)
                    if final_text:
                        write_new_file(file, final_text)

        except Exception as e:
            print(f"无法读取 {file_path}: {e}")