from data_gen import slide_data_gen
from ppt_gen import ppt_gen

data = slide_data_gen('党课培训', page_num=5)
ppt_file = ppt_gen(data)