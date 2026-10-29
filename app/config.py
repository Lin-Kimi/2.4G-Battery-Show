# -*- coding: utf-8 -*-
"""极简设置存储 + 启动日志

位置：%LOCALAPPDATA%\\McHoseBattery\\
  settings.json  用户偏好（目前只有 autostart）
  startup.log    每次启动记一行，用来确认「开机到底有没有起来」
"""
from __future__ import annotations

import datetime
import json
import os
import sys

APP_NAME = "McHoseBattery"

_cache: dict | None = None


def data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def _settings_path() -> str:
    return os.path.join(data_dir(), "settings.json")


def load() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(_settings_path(), "r", encoding="utf-8") as fp:
                data = json.load(fp)
            _cache = data if isinstance(data, dict) else {}
        except Exception:
            _cache = {}
    return _cache


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value) -> bool:  # noqa: A001 - 与 get 成对，语义清晰
    global _cache
    data = dict(load())
    data[key] = value
    _cache = data
    try:
        tmp = _settings_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        os.replace(tmp, _settings_path())
        return True
    except Exception:
        return False


def log_start(hidden: bool) -> None:
    """每次启动追加一行（超过 200KB 就清空重来）"""
    try:
        path = os.path.join(data_dir(), "startup.log")
        try:
            if os.path.getsize(path) > 200 * 1024:
                os.remove(path)
        except OSError:
            pass
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frozen = bool(getattr(sys, "frozen", False))
        line = f"{stamp}  frozen={int(frozen)} hidden={int(hidden)}  argv={sys.argv}\n"
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(line)
    except Exception:
        pass
