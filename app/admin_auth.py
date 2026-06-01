# -*- coding: utf-8 -*-
"""管理员账户管理——简单密码认证"""

import hashlib
import json
import logging
import os
import secrets
from typing import Dict, Optional

from .config import BASE_DIR

ADMIN_CONFIG_PATH = BASE_DIR / "admin_config.json"

DEFAULT_ADMIN_CONFIG: Dict = {
    "password_hash": "",
    "password_salt": "",
    "session_token": "",
}


def _hash_password(password: str, salt: str = "") -> str:
    salted = (password + salt).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def _random_token() -> str:
    return secrets.token_hex(32)


def read_admin_config() -> Dict:
    settings = dict(DEFAULT_ADMIN_CONFIG)
    if ADMIN_CONFIG_PATH.exists():
        try:
            data = json.loads(ADMIN_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update({k: v for k, v in data.items() if v is not None})
        except (OSError, json.JSONDecodeError) as exc:
            logging.getLogger("weekly").warning("admin_config.json read failed: %s", exc)
    return settings


def save_admin_config(settings: Dict) -> None:
    payload = dict(DEFAULT_ADMIN_CONFIG)
    payload.update({k: v for k, v in settings.items() if v is not None})
    ADMIN_CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_password_set() -> bool:
    cfg = read_admin_config()
    return bool(cfg.get("password_hash"))


def verify_password(password: str) -> bool:
    cfg = read_admin_config()
    if not cfg.get("password_hash"):
        return True  # 未设置密码则无需验证
    salt = cfg.get("password_salt", "")
    return cfg["password_hash"] == _hash_password(password, salt=salt)


def set_password(password: str) -> str:
    cfg = read_admin_config()
    salt = secrets.token_hex(16)
    cfg["password_hash"] = _hash_password(password, salt=salt)
    cfg["password_salt"] = salt
    token = _random_token()
    cfg["session_token"] = token
    save_admin_config(cfg)
    return token


def validate_session(token: str) -> bool:
    if not token:
        return False
    cfg = read_admin_config()
    if not cfg.get("password_hash"):
        return False  # 未设置密码时 session 无效，让模板显示设置密码界面
    return cfg.get("session_token") == token


def login(password: str) -> Optional[str]:
    if not verify_password(password):
        return None
    cfg = read_admin_config()
    token = _random_token()
    cfg["session_token"] = token
    save_admin_config(cfg)
    return token


def logout() -> None:
    cfg = read_admin_config()
    cfg["session_token"] = ""
    save_admin_config(cfg)


_SESSION_COOKIE = "admin_token"
_SESSION_MAX_AGE = 86400 * 7  # 7 days


def check_session(request) -> bool:
    token = request.cookies.get(_SESSION_COOKIE, "")
    return validate_session(token)


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        max_age=_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(_SESSION_COOKIE)
