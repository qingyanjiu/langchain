import os
import shutil
# 将源文件递归拷贝到目标文件夹
def copy_files_recursive(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            target_path = os.path.join(target_dir, file)
            
            # 处理重名文件，避免覆盖
            counter = 1
            while os.path.exists(target_path):
                name, ext = os.path.splitext(file)
                target_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.copy2(source_path, target_path)
            print(f"Copied: {source_path} -> {target_path}")

# 示例用法
source_directory = "/Users/louisliu/dev/LLM/知识库"  # 替换为实际源目录
target_directory = "/Users/louisliu/dev/LLM/RAG_DOC_DIST"  # 替换为实际目标目录
copy_files_recursive(source_directory, target_directory)
