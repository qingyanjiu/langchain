from pypdf import PdfReader, PdfWriter

# 读取原始PDF文件
reader = PdfReader("/Users/louisliu/Downloads/和信-中智2023年外包框架合同.pdf")

# 创建一个新的写入器对象
writer = PdfWriter()

# 遍历原始PDF的每一页
for page in reader.pages:
    # 将每一页添加到写入器对象
    writer.add_page(page)

# 遍历每一页的图像，并降低图像质量
for page in writer.pages:
    for img in page.images:
        img.replace(img.image, quality=1)  # 设置图像质量

# 写入新的压缩后的PDF文件
with open("和信-中智2023年外包框架合同.pdf", "wb") as f:
    writer.write(f)