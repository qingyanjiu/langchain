import asyncio
from playwright.async_api import async_playwright
import gradio as gr
from PIL import Image
from io import BytesIO

# 获取二维码，用户扫描登录

# 全局保存状态
qr_status = {"scanned": "等待获取二维码...", "browser": None, "page": None}

pw = None

async def get_qr_code():
    pw = await async_playwright().start()  # 显式启动

    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page()
    qr_status["browser"] = browser
    qr_status["page"] = page

    await page.goto('https://www.srdcloud.cn/')
    iframe_el = page.locator('iframe[title="天翼账户登录"]')
    await iframe_el.wait_for(state='visible', timeout=15000)
    iframe_src = await iframe_el.get_attribute('src')
    await page.goto(iframe_src)

    qr = page.locator('#j-qrcodeImage')
    await qr.wait_for(state='visible', timeout=15000)
    qr_bytes = await qr.screenshot()
    qr_image = Image.open(BytesIO(qr_bytes))  # 转 PIL.Image
    
    qr_status["scanned"] = "等待扫码"
    
    asyncio.create_task(wait_scan(page))

    return qr_image

async def wait_scan(page):
    try:
        await page.wait_for_function(
            """() => {
                const el = document.querySelector('div#J-qrCodeLoginResult');
                return el && !el.classList.contains('hide');
            }""",
            timeout=60*1000
        )
        qr_status["scanned"] = "扫码成功，您已经成功登陆，直接关闭该页面即可"
    except asyncio.TimeoutError:
        qr_status["scanned"] = "超时，请重新点击获取二维码按钮"

async def check_status():
    return qr_status["scanned"]


with gr.Blocks(title="扫码登录") as demo:
    gr.Markdown("### 点击按钮获取登录二维码")
    btn = gr.Button("获取二维码")
    img = gr.Image(type="filepath", label="登录二维码", interactive=False)
    tip = gr.Textbox(label="状态", interactive=False)

    btn.click(fn=get_qr_code, inputs=None, outputs=img)
    
    timer = gr.Timer(value=1.0)  # 每1秒触发
    timer.tick(check_status, outputs=tip)

if __name__ == "__main__":
    demo.launch()