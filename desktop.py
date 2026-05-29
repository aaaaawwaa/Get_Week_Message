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

# ------------------------------------------------------------
# PyInstaller 打包后，将配置/数据库/日志目录重定向到 exe 所在目录
# ------------------------------------------------------------
if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).parent

    # 强制覆盖 app.config 中的路径，让它们指向 exe 旁边的可写目录
    import app.config as _cfg

    _cfg.BASE_DIR = EXE_DIR
    _cfg.DB_PATH = EXE_DIR / "db" / "weekly.db"
    _cfg.LOG_DIR = EXE_DIR / "logs"
    _cfg.LOG_FILE = _cfg.LOG_DIR / "weekly.log"
    _cfg.REPORTS_DIR = EXE_DIR / "static" / "reports"
    _cfg.COVERS_DIR = _cfg.REPORTS_DIR / "covers"
    _cfg.AI_CONFIG_PATH = EXE_DIR / "ai_config.json"

    # 确保目录存在
    _cfg.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _cfg.LOG_DIR.mkdir(parents=True, exist_ok=True)
    _cfg.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _cfg.COVERS_DIR.mkdir(parents=True, exist_ok=True)

    # 如果 ai_config.json 不存在，创建默认空配置（无 API Key）
    if not _cfg.AI_CONFIG_PATH.exists():
        default = {
            "enabled": False,
            "base_url": "",
            "api_key": "",
            "model": "gpt-4o-mini",
            "max_tokens": 600,
            "max_items_per_source": 12,
        }
        _cfg.AI_CONFIG_PATH.write_text(
            json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 重新导入依赖了 config 的模块，让它们拿到新路径
    import importlib
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("app.") and mod_name != "app.config":
            del sys.modules[mod_name]

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
