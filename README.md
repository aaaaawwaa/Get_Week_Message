# 📊 每周热点聚合

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/Schedule-Weekly-orange?logo=clockify" alt="Schedule">
</p>

> 自动聚合多源中文热点，生成美观的静态周报。支持 B 站热门、微博热搜、可配置的 RSS 数据源，可选 AI 智能总结。

## ✨ 特性

- 🔥 **多源聚合** — Bilibili 热门 + 微博热搜 + 灵活可配的 RSS 数据源
- 📡 **RSS 灵活配置** — Web UI 管理数据源，支持添加/移除，预设 20+ 源一键添加
- 🔍 **关键词过滤** — 为时事 RSS 设置关键词白名单，精准筛选感兴趣的内容
- 🤖 **AI 总结** — 可选的 LLM 每周摘要（OpenAI 兼容 API）
- 📊 **图形化仪表盘** — 实时进度条、数据库使用率、系统资源监控
- 📄 **静态周报** — 按数据源独立分栏展示，纯静态 HTML
- 📚 **历史归档** — 自动保留历史周报，支持分页浏览
- ⏰ **定时任务** — 每周日 8:00 自动生成
- 🗄️ **容量管理** — SQLite 限制 2GB，图形化使用率预警
- 🐳 **Docker 一键部署** — 配置和数据自动持久化

## 🚀 快速开始

### Docker（推荐）

```bash
git clone https://github.com/aaaaawwaa/Get_Week_Message.git
cd Get_Week_Message
docker compose up -d
# 浏览器打开 http://127.0.0.1:8000
```

### 本地运行

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/Mac
# .\.venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload
# 浏览器打开 http://127.0.0.1:8000
```

首次运行后打开「设置」→ 点击「▶ 立即抓取并生成」即可生成第一期周报。

## 📡 数据源管理

通过 Web 配置页面（`/config` → 📡 数据源）：

| 操作 | 说明 |
|------|------|
| 添加预设源 | 从下拉框选择，一键添加 |
| 手动添加 | 输入任意 RSS/Atom URL |
| 移除源 | 点击 × 删除（**重新抓取后自动清理该源的旧数据**） |
| 关键词过滤 | 留空 = 不过滤；设置关键词 = 仅保留匹配条目 |
| 调整数量 | 分别控制 B 站、微博、时事各源抓取条数 |

### 已验证可用的直连 RSS 源

| 数据源 | URL |
|--------|-----|
| 人民日报-时政 | `http://www.people.com.cn/rss/politics.xml` |
| 人民日报-社会 | `http://www.people.com.cn/rss/society.xml` |
| 人民日报-国际 | `http://www.people.com.cn/rss/world.xml` |
| 36氪-快讯 | `https://36kr.com/feed` |
| 阮一峰-科技周刊 | `https://www.ruanyifeng.com/blog/atom.xml` |

> ⚠️ rsshub.app 代理类源（澎湃/虎嗅/知乎等）在国内 Docker 环境可能不可达，需自建 RSSHub 实例。

## 📊 系统监控

| 标签页 | 内容 |
|--------|------|
| ⚙️ 通用 | 数据库使用率进度条、周报数量、封面数 |
| 📊 统计 | 数据库详情面板（当前/最大/使用率/剩余）、系统资源、Token 趋势 |
| 📋 日志 | 实时运行日志 |

数据库默认 2GB 上限，超过 60% 黄色预警，超过 80% 红色预警。

## 📁 项目结构

```
├── app/
│   ├── main.py              # FastAPI 入口 + API 路由
│   ├── config.py            # 全局配置
│   ├── data_config.py       # 数据源持久化 + 预设源列表
│   ├── run_weekly.py        # 周报生成 + 进度追踪
│   ├── render.py            # Jinja2 模板渲染
│   ├── storage.py           # SQLite + 容量限制
│   ├── stats.py             # 系统统计 API
│   ├── ai_summary.py        # AI 接口封装
│   ├── http_client.py       # HTTP 客户端 + 4xx 快速失败
│   ├── cover_cache.py       # 封面图缓存
│   ├── admin_auth.py        # 管理员认证
│   ├── scheduler.py         # 定时调度
│   ├── fetchers/            # 数据抓取器
│   │   ├── bilibili.py      #   B 站热门
│   │   ├── weibo.py         #   微博热搜
│   │   └── affairs.py       #   RSS 多源抓取 + 关键词过滤
│   ├── templates/           # Jinja2 模板
│   │   ├── report.html      #   周报详情
│   │   ├── index.html       #   历史列表
│   │   └── config.html      #   设置仪表盘
│   ├── static/reports/      # 生成的静态周报
│   ├── db/                  # SQLite 数据库
│   └── logs/                # 运行日志
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── LICENSE
```

## 🤖 AI 总结

配置页（`/config` → 🤖 AI 配置）中启用，支持 OpenAI / DeepSeek / 通义千问 / 智谱等兼容 API。生成的总结嵌入周报顶部。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

[MIT License](LICENSE)
