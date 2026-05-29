import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ai_summary import read_ai_config_file, save_ai_config_file, test_ai_connection
from .config import LOG_FILE, REPORTS_DIR, TEMPLATE_DIR, ensure_dirs
from .scheduler import start_scheduler

ensure_dirs()

app = FastAPI(title="Weekly Hot Topics")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR), html=True), name="reports")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@app.get("/")
def root():
    return RedirectResponse("/reports/latest.html")


@app.get("/config", response_class=HTMLResponse)
def config_page(request: Request):
    config = read_ai_config_file()
    return templates.TemplateResponse(
        request,
        "config.html",
        {
            "config": config,
            "has_api_key": bool(config.get("api_key")),
        },
    )


@app.post("/api/ai-config", response_class=JSONResponse)
async def save_ai_config(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    existing = read_ai_config_file()
    updated = dict(existing)

    for key in ["enabled", "base_url", "model", "max_tokens", "max_items_per_source"]:
        if key in payload and payload[key] is not None:
            updated[key] = payload[key]

    api_key = str(payload.get("api_key", "")).strip()
    if api_key:
        updated["api_key"] = api_key

    save_ai_config_file(updated)
    return {"ok": True}


@app.post("/api/ai-config/test", response_class=JSONResponse)
async def test_ai_config(request: Request):
    payload = await request.json()
    if payload and not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    existing = read_ai_config_file()
    settings = dict(existing)
    if isinstance(payload, dict):
        for key in ["enabled", "base_url", "model", "max_tokens", "max_items_per_source"]:
            if key in payload and payload[key] is not None:
                settings[key] = payload[key]
        api_key = str(payload.get("api_key", "")).strip()
        if api_key:
            settings["api_key"] = api_key

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

    raw = LOG_FILE.read_text(encoding="utf-8", errors="replace")
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


@app.on_event("startup")
def on_startup():
    start_scheduler()
