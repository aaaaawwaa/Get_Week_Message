import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ai_summary import read_ai_config_file, save_ai_config_file, test_ai_connection
from .config import LOG_FILE, REPORTS_DIR, TEMPLATE_DIR, ensure_dirs
from .data_config import apply_data_config_to_module, read_data_config, save_data_config
from .scheduler import start_scheduler
from .admin_auth import (
    check_session,
    clear_session_cookie,
    is_password_set,
    login,
    logout,
    set_password,
    set_session_cookie,
)

_MAX_BODY_SIZE = 100_000  # 100KB limit for POST bodies


def _merge_ai_payload(payload: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    """合并 AI 配置 payload 到现有配置，避免 save/test 重复代码"""
    merged = dict(existing)
    for key in ["enabled", "base_url", "model", "max_tokens", "max_items_per_source"]:
        if key in payload and payload[key] is not None:
            merged[key] = payload[key]
    api_key = str(payload.get("api_key", "")).strip()
    if api_key:
        merged["api_key"] = api_key
    return merged


ensure_dirs()
apply_data_config_to_module()
app = FastAPI(title="Weekly Hot Topics")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# 挂载静态周报目录（可能为空，不影响动态路由）
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR), html=True), name="reports")


@app.get("/")
def root():
    # 如果还没有周报，跳转到欢迎/配置页
    latest = REPORTS_DIR / "latest.html"
    if latest.exists():
        return RedirectResponse("/reports/latest.html")
    return RedirectResponse("/config")


@app.get("/config", response_class=HTMLResponse)
def config_page(request: Request):
    config = read_ai_config_file()
    data_config = read_data_config()
    logged_in = check_session(request)
    password_set = is_password_set()
    return templates.TemplateResponse(
        request,
        "config.html",
        {
            "config": config,
            "data_config": data_config,
            "has_api_key": bool(config.get("api_key")),
            "logged_in": logged_in,
            "password_set": password_set,
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    weeks = []
    try:
        from .storage import get_week_summaries
        raw = get_week_summaries()
        weeks = [
            {
                "week_start": row["week_start"],
                "total": row["total"],
                "link": f"/reports/{row['week_start']}.html",
            }
            for row in raw
        ]
    except Exception:
        pass
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "weeks": weeks,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@app.post("/api/ai-config", response_class=JSONResponse)
async def save_ai_config(request: Request):
    body = await request.body()
    if len(body) > _MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="payload too large")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    existing = read_ai_config_file()
    updated = _merge_ai_payload(payload, existing)
    save_ai_config_file(updated)
    return {"ok": True}


@app.post("/api/ai-config/test", response_class=JSONResponse)
async def test_ai_config(request: Request):
    body = await request.body()
    if len(body) > _MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="payload too large")
    payload = await request.json()
    if payload and not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    existing = read_ai_config_file()
    settings = _merge_ai_payload(payload, existing) if isinstance(payload, dict) else existing
    ok, message = test_ai_connection(settings)
    return {"ok": ok, "message": message}


@app.get("/api/ai-config/logs", response_class=JSONResponse)
def get_ai_logs():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        return {
            "lines": [],
            "summary": {
                "total_fetch": 0,
                "ai_calls": 0,
                "last_ai_tokens": 0,
                "last_ai_time": 0,
            },
        }

    # 只读取文件末尾部分以避免大文件 OOM
    max_read_bytes = 200 * 1024  # 200KB
    file_size = LOG_FILE.stat().st_size
    with LOG_FILE.open("rb") as fh:
        if file_size > max_read_bytes:
            fh.seek(file_size - max_read_bytes)
            # 跳到最近一行的开头
            leftover = fh.readline()
            raw = (leftover + fh.read()).decode("utf-8", errors="replace")
        else:
            raw = fh.read().decode("utf-8", errors="replace")
    all_lines = raw.strip().splitlines()
    recent_lines = all_lines[-100:]

    fetch_oks = []
    ai_success = []
    for line in recent_lines:
        if "fetch ok:" in line:
            fetch_oks.append(line)
        if "ai summary success:" in line:
            ai_success.append(line)

    summary = {
        "total_fetch": len(fetch_oks),
        "ai_calls": len(ai_success),
        "last_ai_tokens": 0,
        "last_ai_time": 0,
    }

    if ai_success:
        last_line = ai_success[-1]
        m = re.search(r"elapsed=([\d.]+)s.*total_tokens=(\d+)", last_line)
        if m:
            summary["last_ai_time"] = round(float(m.group(1)), 2)
            summary["last_ai_tokens"] = int(m.group(2))

    # Build daily token data from full log
    daily_tokens: Dict[str, int] = defaultdict(int)
    daily_calls: Dict[str, int] = defaultdict(int)

    for line in all_lines:
        m = re.search(r"^(\d{4}-\d{2}-\d{2})\s+.*ai summary success:.*total_tokens=(\d+)", line)
        if m:
            day = m.group(1)
            tokens = int(m.group(2))
            daily_tokens[day] += tokens
            daily_calls[day] += 1

    now = datetime.now()
    daily_chart = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_chart.append({
            "date": day,
            "tokens": daily_tokens.get(day, 0),
            "calls": daily_calls.get(day, 0),
        })

    return {"lines": recent_lines[-60:], "summary": summary, "daily_chart": daily_chart}


@app.get("/api/data-config", response_class=JSONResponse)
def get_data_config():
    return read_data_config()


@app.post("/api/data-config", response_class=JSONResponse)
async def save_data_source_config(request: Request):
    body = await request.body()
    if len(body) > _MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="payload too large")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")
    existing = read_data_config()
    for key in ["bilibili_limit", "weibo_limit", "github_limit", "affairs_limit", "affairs_sources", "affairs_keywords"]:
        if key in payload and payload[key] is not None:
            existing[key] = payload[key]
    save_data_config(existing)
    apply_data_config_to_module()
    # 保存后自动在后台触发一次抓取，新数据源立即生效
    import threading
    from .run_weekly import main as run_weekly
    t = threading.Thread(target=run_weekly, daemon=True)
    t.start()
    return {"ok": True, "message": "配置已保存，后台抓取已启动"}


@app.get("/api/overview", response_class=JSONResponse)
def get_overview():
    """Dashboard overview data"""
    from .storage import get_week_summaries

    weeks = []
    latest_week = None
    try:
        raw = get_week_summaries()
        weeks = [{"week_start": r["week_start"], "total": r["total"]} for r in raw]
        if weeks:
            latest_week = weeks[0]
    except Exception:
        pass

    # Check reports dir
    reports_count = len(list(REPORTS_DIR.glob("*.html"))) if REPORTS_DIR.exists() else 0

    # Check AI config
    ai_cfg = read_ai_config_file()

    return {
        "weeks": weeks,
        "latest_week": latest_week,
        "reports_count": reports_count,
        "ai_enabled": ai_cfg.get("enabled", False),
        "ai_configured": bool(ai_cfg.get("api_key")),
    }


# ===== 管理员认证 =====

@app.post("/api/auth/login", response_class=JSONResponse)
async def auth_login(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid payload")
    password = str(body.get("password", ""))
    token = login(password)
    if token:
        resp = JSONResponse({"ok": True})
        set_session_cookie(resp, token)
        return resp
    raise HTTPException(status_code=401, detail="密码错误")


@app.post("/api/auth/logout", response_class=JSONResponse)
def auth_logout():
    logout()
    resp = JSONResponse({"ok": True})
    clear_session_cookie(resp)
    return resp


@app.post("/api/auth/set-password", response_class=JSONResponse)
async def auth_set_password(request: Request):
    # 首次设置密码不需要 session；修改密码需要 session
    if is_password_set() and not check_session(request):
        raise HTTPException(status_code=401, detail="请先登录")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid payload")
    password = str(body.get("password", "")).strip()
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="密码至少 4 位")
    token = set_password(password)
    resp = JSONResponse({"ok": True})
    set_session_cookie(resp, token)
    return resp


@app.get("/api/auth/status", response_class=JSONResponse)
def auth_status(request: Request):
    return {"logged_in": check_session(request), "password_set": is_password_set()}


# ===== 预设数据源 =====

@app.get("/api/source-presets", response_class=JSONResponse)
def get_source_presets():
    from .data_config import PRESET_SOURCES, PRESET_KEYWORDS
    return {
        "sources": PRESET_SOURCES,
        "keyword_sets": PRESET_KEYWORDS,
    }


# ===== 系统统计 =====

@app.get("/api/stats/system", response_class=JSONResponse)
def api_system_stats():
    from .stats import get_system_stats
    return get_system_stats()


@app.get("/api/stats/sources", response_class=JSONResponse)
def api_source_stats():
    from .stats import get_source_stats
    return get_source_stats()


@app.get("/api/stats/summary", response_class=JSONResponse)
def api_fetch_summary():
    from .stats import get_fetch_summary
    return get_fetch_summary()


@app.post("/api/run-weekly", response_class=JSONResponse)
def run_weekly_api():
    """手动触发周报生成（配置页的立即抓取按钮）"""
    from .run_weekly import main as run_weekly
    import threading
    threading.Thread(target=run_weekly, daemon=True).start()
    return {"ok": True, "message": "已在后台启动抓取"}


@app.get("/api/run-weekly/status", response_class=JSONResponse)
def run_weekly_status():
    from .run_weekly import get_run_progress
    return get_run_progress()


@app.get("/api/scheduler/next", response_class=JSONResponse)
def scheduler_next_run():
    from .scheduler import get_next_run_time
    return {"next_run": get_next_run_time()}


@app.on_event("startup")
def on_startup():
    from .data_config import apply_data_config_to_module
    apply_data_config_to_module()
    start_scheduler()
