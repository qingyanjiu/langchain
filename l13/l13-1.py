'''
Playwright 是一个开源的自动化框架，它可以让你模拟真实用户操作网页，帮助开发者和测试者自动化网页交互和测试。
用简单的话说，它就像一个“机器人”，可以按照你给的指令去浏览网页、点击按钮、填写表单、读取页面内容等等，就像一个真实的用户在使用浏览器一样
pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install chromium

https://playwright.dev/python/docs/locators
'''

from playwright.sync_api import sync_playwright

def run():
    # 使用Playwright上下文管理器
    with sync_playwright() as p:
        # 使用Chromium，但你也可以选择firefox或webkit
        browser = p.chromium.launch(headless=False)
        
        # 创建一个新的页面
        page = browser.new_page()
        
        # 导航到指定的URL
        page.goto('https://www.bilibili.com/')
        
        # 获取并打印页面标题
        page.click("text=登录")
        page.get_by_placeholder("请输入账号").fill("xxx")
        page.get_by_placeholder("请输入密码").fill("xxx")
        page.locator('//*/div[4]/div/div[4]/div[2]/div[2]/div[2]').click()
        
        # 关闭浏览器
        # browser.close()

if __name__ == "__main__":
    run()