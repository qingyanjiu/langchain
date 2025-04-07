import os
import re
# 先将 RAG_DOC_DIST_TXT 中文件拷贝到 RAG_DOC_FINAL
def clean_txt_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                
                # 如果文件名不包含“应急预案”，则删除文件
                if "应急预案" not in file:
                    os.remove(file_path)
                    print(f"Deleted file (name mismatch): {file_path}")
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 如果文件字符数少于1000，则删除文件
                if len(content) < 1000:
                    os.remove(file_path)
                    print(f"Deleted small file: {file_path}")
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # 跳过开头的所有空行
                start_index = 0
                while start_index < len(lines) and lines[start_index].strip() == "":
                    start_index += 1
                
                new_lines = []
                skip = False
                for i, line in enumerate(lines):
                    if i == start_index + 1:
                        skip = True  # 开始跳过从第二行到第一个大标题1
                    if re.match(r"^.*[1|１]", line):  # 检测大标题1
                        skip = False
                    if not skip:
                        new_lines.append(line)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                # 再次检查文件大小
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) < 1000:
                    os.remove(file_path)
                    print(f"Deleted small file after processing: {file_path}")
                    continue

                print(f"Processed: {file_path}")

# 示例用法
directory = "/Users/louisliu/dev/LLM/RAG_DOC_FINAL"  # 替换为实际目录路径
clean_txt_files(directory)
