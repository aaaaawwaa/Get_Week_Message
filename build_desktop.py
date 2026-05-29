"""
构建桌面版安装包
用法: python build_desktop.py

注意: 构建前会自动用示例配置替换真实的 ai_config.json，
      确保你的 API Key 不会被打包进 exe。
      构建完成后自动恢复你的真实配置。
"""

import os
import shutil
import subprocess
import sys
import json

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

AI_CONFIG = "app/ai_config.json"
AI_CONFIG_EXAMPLE = "app/ai_config.example.json"
AI_CONFIG_BAK = "app/ai_config.json.buildbak"

# ---------- 打包前：保护 API Key ----------
has_real_config = os.path.isfile(AI_CONFIG)
if has_real_config:
    print("🔒 检测到真实 ai_config.json，正在保护 API Key...")
    shutil.copy2(AI_CONFIG, AI_CONFIG_BAK)
    if os.path.isfile(AI_CONFIG_EXAMPLE):
        shutil.copy2(AI_CONFIG_EXAMPLE, AI_CONFIG)
        print("   ✅ 已替换为示例配置（无 API Key）")
    else:
        # 没有示例文件，创建一个空配置
        empty = {"enabled": False, "base_url": "", "api_key": "", "model": "gpt-4o-mini", "max_tokens": 600, "max_items_per_source": 12}
        with open(AI_CONFIG, "w", encoding="utf-8") as f:
            json.dump(empty, f, ensure_ascii=False, indent=2)
        print("   ✅ 已替换为空配置（无 API Key）")
else:
    print("ℹ️  未检测到 ai_config.json，跳过保护")
    if not os.path.isfile(AI_CONFIG_EXAMPLE):
        empty = {"enabled": False, "base_url": "", "api_key": "", "model": "gpt-4o-mini", "max_tokens": 600, "max_items_per_source": 12}
        with open(AI_CONFIG_EXAMPLE, "w", encoding="utf-8") as f:
            json.dump(empty, f, ensure_ascii=False, indent=2)

# 安装 PyInstaller
subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

# 执行打包
subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",          # 单文件 exe
    "--windowed",         # 无控制台窗口
    "--name", "每周热点聚合",
    "--add-data", f"app{os.pathsep}app",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "desktop.py",
], check=True)

print("\n✅ 打包完成！安装包在 dist/每周热点聚合.exe")

# ---------- 打包后：恢复真实 API Key ----------
if has_real_config and os.path.isfile(AI_CONFIG_BAK):
    shutil.move(AI_CONFIG_BAK, AI_CONFIG)
    print("🔓 已恢复你的真实 ai_config.json（API Key 安全回归）")
elif has_real_config:
    print("⚠️  备份文件丢失，请检查 app/ai_config.json 是否有误")
