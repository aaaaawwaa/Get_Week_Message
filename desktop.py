"""
桌面版启动入口 —— 内嵌 FastAPI 服务 + 系统原生窗口
"""

import json
import os
import sys
import threading
from pathlib import Path

import webview
import uvicorn

# ---------- PyInstaller 打包后，数据目录重定向到 exe 旁边 ----------
if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).parent
    DATA_DIR = EXE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 用环境变量传递路径，各模块不需要重载
    os.environ["WEEKLY_DATA_DIR"] = str(DATA_DIR)

    # 如果 ai_config.json 不存在，创建默认空配置
    cfg_path = DATA_DIR / "ai_config.json"
    if not cfg_path.exists():
        default = {
            "enabled": False,
            "base_url": "",
            "api_key": "",
            "model": "gpt-4o-mini",
            "max_tokens": 600,
            "max_items_per_source": 12,
        }
        cfg_path.write_text(
            json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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
