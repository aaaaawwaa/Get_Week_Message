"""
桌面版启动入口 —— 内嵌 FastAPI 服务 + 系统原生窗口
"""

import threading
import webview
import uvicorn
from app.main import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    webview.create_window(
        "每周热点聚合",
        "http://127.0.0.1:8000",
        width=1200,
        height=800,
        resizable=True,
    )
    webview.start()
