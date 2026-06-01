# -*- coding: utf-8 -*-
"""数据源配置持久化存储"""

import json
import logging
from typing import Any, Dict, List

from .config import (
    BASE_DIR,
    BILIBILI_LIMIT,
    CURRENT_AFFAIRS_KEYWORDS,
    CURRENT_AFFAIRS_LIMIT,
    CURRENT_AFFAIRS_SOURCES,
    WEIBO_LIMIT,
)

DATA_CONFIG_PATH = BASE_DIR / "data_sources.json"

# 预设常见中文 RSS 数据源（按分类浏览）
# ⚠️ 标注: ✅=Docker内实测通过  ⚠️=需代理/自建rsshub  ❌=已失效已移除
PRESET_SOURCES: List[Dict[str, str]] = [
    # === 官方媒体（Docker 实测通过） ===
    {"name": "人民日报-时政", "url": "http://www.people.com.cn/rss/politics.xml"},      # ✅
    {"name": "人民日报-社会", "url": "http://www.people.com.cn/rss/society.xml"},       # ✅
    {"name": "人民日报-国际", "url": "http://www.people.com.cn/rss/world.xml"},         # ✅
    # === 科技 & 独立博客（Docker 实测通过） ===
    {"name": "36氪-快讯", "url": "https://36kr.com/feed"},                              # ✅
    {"name": "阮一峰-科技周刊", "url": "https://www.ruanyifeng.com/blog/atom.xml"},     # ✅
    # === 需要自建 RSSHub 或代理访问（rsshub.app 在国内Docker环境不可达） ===
    {"name": "澎湃新闻-时事", "url": "https://rsshub.app/thepaper/latest"},             # ⚠️
    {"name": "虎嗅网-24小时", "url": "https://rsshub.app/huxiu/article"},               # ⚠️
    {"name": "观察者网-要闻", "url": "https://rsshub.app/guancha"},                     # ⚠️
    {"name": "知乎-每日精选", "url": "https://rsshub.app/zhihu/daily"},                 # ⚠️
    {"name": "豆瓣-电影热门", "url": "https://rsshub.app/douban/movie/playing"},        # ⚠️
    {"name": "Hacker News", "url": "https://rsshub.app/hackernews"},                    # ⚠️
    {"name": "V2EX-最热", "url": "https://rsshub.app/v2ex/topics/latest"},              # ⚠️
    {"name": "新浪新闻-要闻", "url": "https://rsshub.app/sina/news/focus"},             # ⚠️
    {"name": "腾讯新闻-热点", "url": "https://rsshub.app/tencent/news"},                # ⚠️
    {"name": "网易新闻-热点", "url": "https://rsshub.app/netease/news"},                # ⚠️
    # === 已失效，仅供参考 ===
    # 新华社系列(news.cn) → 返回403 · 环球网系列(huanqiu.com) → 404
    # 央视网(cctv.com) → 404 · 百度新闻(news.baidu.com) → 空RSS
    # FeedX代理(feedx.net) → Docker内URLError · 虎嗅直接(huxiu.com) → 超时
]

# 预设关键词过滤建议
PRESET_KEYWORDS: Dict[str, List[str]] = {
    "时政": ["时政", "政策", "国务院", "中央", "国家", "外交", "会议"],
    "科技": ["AI", "人工智能", "芯片", "华为", "科技", "苹果", "微软", "谷歌"],
    "经济": ["经济", "金融", "股市", "GDP", "通胀", "关税", "贸易"],
    "社会": ["社会", "民生", "教育", "医疗", "住房", "就业", "养老"],
}


DEFAULT_DATA_CONFIG: Dict[str, Any] = {
    "bilibili_limit": BILIBILI_LIMIT,
    "weibo_limit": WEIBO_LIMIT,
    "affairs_limit": CURRENT_AFFAIRS_LIMIT,
    "affairs_sources": list(CURRENT_AFFAIRS_SOURCES),
    "affairs_keywords": list(CURRENT_AFFAIRS_KEYWORDS),
}


def read_data_config() -> Dict[str, Any]:
    settings = dict(DEFAULT_DATA_CONFIG)
    if DATA_CONFIG_PATH.exists():
        try:
            data = json.loads(DATA_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update({k: v for k, v in data.items() if v is not None})
        except (OSError, json.JSONDecodeError) as exc:
            logging.getLogger("weekly").warning("data_sources.json read failed: %s", exc)
    return settings


def save_data_config(settings: Dict[str, Any]) -> None:
    payload = dict(DEFAULT_DATA_CONFIG)
    payload.update({k: v for k, v in settings.items() if v is not None})
    DATA_CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def apply_data_config_to_module() -> None:
    """将持久化的数据源配置覆盖到 config 模块的变量上"""
    from . import config as cmod

    data = read_data_config()
    cmod.BILIBILI_LIMIT = data.get("bilibili_limit", cmod.BILIBILI_LIMIT)
    cmod.WEIBO_LIMIT = data.get("weibo_limit", cmod.WEIBO_LIMIT)
    cmod.CURRENT_AFFAIRS_LIMIT = data.get("affairs_limit", cmod.CURRENT_AFFAIRS_LIMIT)
    cmod.CURRENT_AFFAIRS_SOURCES = data.get("affairs_sources", cmod.CURRENT_AFFAIRS_SOURCES)
    cmod.CURRENT_AFFAIRS_KEYWORDS = data.get("affairs_keywords", cmod.CURRENT_AFFAIRS_KEYWORDS)

