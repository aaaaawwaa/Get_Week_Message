"""
构建桌面版安装包
用法: python build_desktop.py

工作原理:
1. 将你的真实 ai_config.json（含 API Key）移到临时备份
2. 删除 app/ai_config.json，确保它不被打包进 exe
3. 用 PyInstaller 构建 exe（exe 内部无任何 API Key）
4. 恢复你的真实 ai_config.json
5. exe 首次运行时自动创建空白配置，用户自己在界面填写
"""

import os
import shutil
import subprocess
import sys

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

AI_CONFIG = "app/ai_config.json"
AI_CONFIG_BAK = os.path.join(os.environ["TEMP"], "ai_config.json.buildbak")

# ---------- 打包前：彻底移除 API Key ----------
has_real_config = os.path.isfile(AI_CONFIG)
if has_real_config:
    print("🔒 检测到 ai_config.json，正在移除以保护 API Key...")
    shutil.copy2(AI_CONFIG, AI_CONFIG_BAK)
    os.remove(AI_CONFIG)
    print("   ✅ 已从项目中移除（备份到临时目录）")
else:
    print("ℹ️  未检测到 ai_config.json，无需保护")

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
print("   exe 内部已无任何 API Key 信息，请放心分发")

# ---------- 打包后：恢复本地 API Key ----------
if has_real_config and os.path.isfile(AI_CONFIG_BAK):
    shutil.move(AI_CONFIG_BAK, AI_CONFIG)
    print("🔓 已恢复你的本地 ai_config.json")
    print("   下次打包前会自动重复此流程")
