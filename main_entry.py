"""
syserroranl 打包入口 - 用于 PyInstaller 打包
启动 FastAPI + uvicorn 服务，并自动打开浏览器
"""
import sys
import os
import threading
import time
import webbrowser

# 关键：让 PyInstaller 打包后能找到正确的路径
def get_base_path():
    """获取资源根目录（兼容开发环境和 PyInstaller 打包后的环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，资源在 _MEIPASS 临时目录
        return sys._MEIPASS
    else:
        # 开发环境，使用脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))

# 设置工作目录，让 app.py 中的相对路径正常工作
BASE_PATH = get_base_path()
os.chdir(BASE_PATH)

# 将 base path 加入模块搜索路径
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# 数据库存放在用户数据目录（可写），而非 _MEIPASS（只读）
if getattr(sys, 'frozen', False):
    USER_DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    # 覆盖数据库路径
    os.environ['SYSERRORANL_DB_PATH'] = os.path.join(USER_DATA_DIR, 'syserroranl.db')


PORT = 8000
HOST = "127.0.0.1"


def open_browser():
    """延迟 2 秒后打开浏览器"""
    time.sleep(2)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    # 在后台线程打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 启动 uvicorn
    import uvicorn
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
