# 📊 每周热点聚合

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/Schedule-Weekly-orange?logo=clockify" alt="Schedule">
</p>

自动聚合多源中文热点，生成美观的静态周报页面。支持 B 站热门、微博热搜、人民网时事 RSS，可选 AI 智能总结。

## ✨ 特性

- 🔥 **多源聚合** — Bilibili 热门 + 微博热搜 + 人民网时事 RSS
- 🤖 **AI 总结** — 可选的 LLM 每周摘要，支持 OpenAI 兼容 API
- 📄 **静态周报** — 生成纯静态 HTML，无需运行时数据库查询
- 📚 **历史归档** — 自动保留历史周报，支持搜索和分页浏览
- 🎨 **现代 UI** — 响应式布局，双栏对比展示，封面图缓存
- ⏰ **定时任务** — APScheduler 内置调度，也支持系统 crontab
- 🐳 **Docker 部署** — 一键构建运行，数据持久化
- 🖥️ **桌面应用** — PyWebView 原生窗口，可打包为独立 exe

## 🚀 快速开始

### 本地运行

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# 2. 安装依赖
pip install -r requirements.txt

# 3. 生成一次周报
python -m app.run_weekly

# 4. 启动 Web 服务
uvicorn app.main:app --reload

# 5. 浏览器打开
# http://127.0.0.1:8000
```

### Docker 部署

```bash
docker compose up -d
```

访问 `http://127.0.0.1:8000`。日志、数据库、周报和配置均持久化到宿主机。

### 桌面应用

```bash
# 安装依赖
pip install pywebview

# 启动桌面窗口（原生系统 WebView）
python desktop.py
```

**打包为独立 exe（给没有 Python 的人用）：**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "每周热点聚合" desktop.py
```

生成的可执行文件在 `dist/每周热点聚合.exe`。首次启动会自动打开浏览器窗口加载本机服务。

## 📁 项目结构

```
├── app/
│   ├── main.py              # FastAPI 入口 + API 路由
│   ├── config.py            # 配置（数据源、限制、缓存）
│   ├── scheduler.py         # APScheduler 周调度
│   ├── run_weekly.py        # 手动触发生成周报
│   ├── render.py            # Jinja2 模板渲染
│   ├── storage.py           # SQLite 数据存储
│   ├── ai_summary.py        # AI 接口封装 + Token 日志
│   ├── http_client.py       # HTTP 客户端 + 重试
│   ├── cover_cache.py       # 封面图缓存
│   ├── logging_utils.py     # 日志工具
│   ├── fetchers/            # 数据抓取器
│   │   ├── bilibili.py      #   B 站热门
│   │   ├── weibo.py         #   微博热搜
│   │   └── affairs.py       #   人民网 RSS
│   ├── templates/           # Jinja2 页面模板
│   │   ├── report.html      #   周报详情页
│   │   ├── index.html       #   历史列表页
│   │   └── config.html      #   AI 配置页
│   ├── static/reports/      # 生成的静态周报
│   ├── db/                  # SQLite 数据库
│   └── logs/                # 运行日志
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── LICENSE
```

## 🔧 配置

### 数据源

编辑 `app/config.py`，可调整抓取数量和过滤关键词：

```python
BILIBILI_LIMIT = 30           # B 站抓取条数
WEIBO_LIMIT = 30              # 微博抓取条数
CURRENT_AFFAIRS_LIMIT = 20    # 时事抓取条数

CURRENT_AFFAIRS_SOURCES = [
    {"name": "人民日报-时政", "url": "http://www.people.com.cn/rss/politics.xml"},
    {"name": "人民日报-社会", "url": "http://www.people.com.cn/rss/society.xml"},
    {"name": "人民日报-国际", "url": "http://www.people.com.cn/rss/world.xml"},
]

CURRENT_AFFAIRS_KEYWORDS = ["时政", "政策", "国务院", "中央", "外交", "会议"]
```

### AI 总结

1. 通过 Web UI 配置：打开 `http://127.0.0.1:8000/config`
2. 或复制 `app/ai_config.example.json` 为 `app/ai_config.json`，填入 API 信息：

```json
{
  "enabled": true,
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model": "gpt-4o-mini",
  "max_tokens": 600,
  "max_items_per_source": 12
}
```

支持所有 OpenAI 兼容 API（DeepSeek、通义千问、智谱等）。

### 定时任务

**方式一（内置）**：项目启动后自动注册 APScheduler，每周日 8:00 执行。

**方式二（系统级）**：
- Linux: 添加 crontab `0 8 * * 0 cd /path/to/project && python -m app.run_weekly`
- Windows: 任务计划程序中新建每周任务

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

[MIT License](LICENSE)
1. 进入虚拟环境(PowerShell):
   .\.venv\Scripts\Activate.ps1
2. 安装依赖:
   pip install -r requirements.txt
3. 手动生成一次周报:
   python -m app.run_weekly
4. 启动 Web 服务查看:
   uvicorn app.main:app --reload
5. 浏览器打开(主页为最新周报):
   http://127.0.0.1:8000

## 一键启动（Docker）
```powershell
docker compose up -d
```
首次会自动构建，之后后台运行。日志、数据库、周报和 AI 配置均持久化到宿主机目录。

历史记录入口为 /reports/index.html。

## 时事热点来源配置
在 app/config.py 中设置 CURRENT_AFFAIRS_SOURCES 列表，例如:

```python
CURRENT_AFFAIRS_SOURCES = [
   {"name": "source-a", "url": "<rss_url_here>"},
   {"name": "source-b", "url": "<rss_url_here>"},
]
```

关键词过滤可在 CURRENT_AFFAIRS_KEYWORDS 中调整。

## AI 每周总结配置
你也可以通过 Web 页面配置与测试: http://127.0.0.1:8000/config

1. 复制 app/ai_config.example.json 为 app/ai_config.json。
2. 填入你的 AI API 配置并设置 enabled 为 true。
3. 重新运行 python -m app.run_weekly 生成总结。

## Windows 任务计划
1. 新建基本任务，触发器选择“每周”，星期日，08:00。
2. 操作选择“启动程序”。
3. 程序或脚本填 .venv\Scripts\python.exe。
4. 添加参数填 -m app.run_weekly。
5. 起始于填写项目根目录。
