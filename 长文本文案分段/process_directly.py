# 直接通过代码处理
from docx import Document
import re
import os
import json
doc_dir="/content/drive/MyDrive/yingji"
txt_path ="dist.txt"
stop_path = "delete_str.txt"
json_path = "dist.json"

def load_stop():
  with open(stop_path,'r')as f_stop:
    stop_words=[line.strip() for line in f_stop]
  return set(stop_words)

qr=[]
txt_list=[]
for doc in os.listdir(doc_dir):
  text = []
  if doc.endswith(".docx"):
    doc_path = os.path.join(doc_dir,doc)
    try:
      doc_res=Document(doc_path)
      stop_words =load_stop()
      for para in doc_res.paragraphs:
        if(para.text.strip()!=""):
          temp_txt = re.sub("\s","",para.text).replace("\ue004", "").replace("\ue010",'')
          temp_txt = [word for word in temp_txt if word not in stop_words]
          text.append("".join(temp_txt))
    except Exception as e:
      continue
    # print(text)
  if len(text)>=1:
    que={'question':text[0],'response':''.join(text[1:len(text)])}
    txt_list.append(''.join(text))
    qr.append(que)
    
print(txt_list,len(txt_list))
with open(txt_path,'w')as f:
  for item in qr:
    f.write(f"{item}\n")

with open(json_path,'w')as f_json:
  json.dump(qr, f_json, ensure_ascii=False, indent=2)