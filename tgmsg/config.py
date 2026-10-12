"""Хранение настроек в ~/.tgmsg.json — чтобы не набирать флаги каждый раз.

Файл создаётся после первого запуска; дальше его значения подставляются
как дефолты (и в флаговом режиме, и в интерактивном мастере).
"""
import json
from pathlib import Path

CONFIG_NAME = ".tgmsg.json"

# Ключи, которые вообще могут жить в конфиге
KNOWN_KEYS = (
    "text",
    "count",
    "speed",
    "delay",
    "paste_delay",
    "prepare",
    "stop_key",
    "send_key",
    "paste_hotkey",
)


def config_path() -> Path:
    return Path.home() / CONFIG_NAME


def load_config() -> dict:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in KNOWN_KEYS}


def save_config(data: dict) -> str | None:
    """Сохраняет только известные ключи. Возвращает путь или None при ошибке."""
    clean = {k: data[k] for k in KNOWN_KEYS if data.get(k) not in (None, "")}
    try:
        config_path().write_text(
            json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(config_path())
    except Exception:
        return None
