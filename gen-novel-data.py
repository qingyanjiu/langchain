import json
import re

def parse_novel(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    novel_data = []
    current_volume = ""
    current_chapter = ""
    current_line = ""

    volume_pattern = re.compile(r'^第[一二三四五六七八九十]+卷')
    chapter_pattern = re.compile(r'^第[一二三四五六七八九十]+章')

    for line in lines:
        line = line.strip()
        if volume_pattern.match(line):
            if current_volume and current_volume != line:
                if current_line:
                    entry = {
                        "output": f'{current_line}'
                    }
                    novel_data.append(entry)
                    current_line = ''
                    current_volume = line
                    current_chapter = ''
            else:
                current_volume = line
            
        elif chapter_pattern.match(line):
            current_chapter = line
            if current_line:
                entry = {
                    "output": f'{current_line}'
                }
                novel_data.append(entry)
                current_line = ''
        elif line != '\n':
            if current_line:
                current_line += f"\n{line}"
            else:
                current_line = f"{current_volume}\n{current_chapter}"

    return novel_data

file_path = '/Users/louisliu/Downloads/1.txt'
novel_data = parse_novel(file_path)

output_file = '/Users/louisliu/dev/AI_projects/langchain/novel_data.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(novel_data, f, ensure_ascii=False, indent=4)