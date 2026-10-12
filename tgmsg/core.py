"""Ядро tgmsg: логика отправки, не привязанная к CLI.

Сделано специально так: если захочешь позже навесить GUI (CustomTkinter
и т.п.) — достаточно вызвать эти же функции из окна, ничего не переписывая.
"""
from __future__ import annotations

import importlib
import sys
import time
from dataclasses import dataclass
from enum import Enum
from threading import Event

# macOS вставляет через Cmd+V, остальные — Ctrl+V
PASTE_BY_PLATFORM = {"darwin": "cmd+v"}
DEFAULT_PASTE_HOTKEY = "ctrl+v"


class Speed(str, Enum):
    """Пресеты скорости отправки: пауза между сообщениями."""

    slow = "slow"      # 1 с
    normal = "normal"  # 0.4 с
    fast = "fast"      # 0.2 с
    max = "max"        # 0.08 с


SPEED_DELAYS: dict = {
    Speed.slow: 1.0,
    Speed.normal: 0.4,
    Speed.fast: 0.2,
    Speed.max: 0.08,
}


def paste_hotkey_for_platform() -> str:
    return PASTE_BY_PLATFORM.get(sys.platform, DEFAULT_PASTE_HOTKEY)


def _load(name: str):
    """Ленивый импорт опциональной зависимости с понятной ошибкой.

    Ленивость нужна, чтобы `--dry-run` работал даже без keyboard/pyperclip
    (например, в CI или чтобы просто посмотреть, что утилита умеет).
    """
    try:
        return importlib.import_module(name)
    except Exception as e:  # ImportError и ошибки инициализации (Linux без root и т.п.)
        raise RuntimeError(
            f"Не удалось загрузить модуль «{name}» ({type(e).__name__}: {e}).\n"
            f"Установи зависимости: pip install -r requirements.txt\n"
            f"Подсказки: на Linux модулю keyboard нужны root-права (sudo) и X11-сеанс;\n"
            f"на macOS терминалу нужны разрешения Accessibility и Input Monitoring."
        ) from e


@dataclass
class Settings:
    """Все параметры запуска в одном объекте — удобно передавать из GUI."""

    text: str
    count: int
    delay: float           # пауза после каждой отправки, с
    paste_delay: float     # пауза между вставкой и Enter, с
    prepare: float         # отсчёт до старта, с
    stop_key: str = "esc"
    send_key: str = "enter"          # enter | ctrl+enter
    paste_hotkey: str | None = None  # None -> определить по ОС


class Stopper:
    """Аварийная остановка по клавише.

    Комбинирует два механизма: обработчик хоткея (событие из потока
    keyboard) и опрос is_pressed во время «умного» сна мелкими шагами.
    Так стоп срабатывает даже во время паузы между сообщениями.
    """

    def __init__(self, key: str, enabled: bool = True):
        self.key = key
        self.enabled = enabled
        self.event = Event()
        self._kb = None
        self._activated = False

    def activate(self) -> str | None:
        """Регистрирует хоткей. Возвращает текст ошибки, если не получилось."""
        if not self.enabled or self._activated:
            return None
        kb = _load("keyboard")
        self._kb = kb
        self._activated = True
        try:
            kb.add_hotkey(self.key, self.event.set)
            return None
        except Exception as e:
            return f"{type(e).__name__}: {e}"

    def triggered(self) -> bool:
        if self.event.is_set():
            return True
        if self._kb is not None:
            try:
                return bool(self._kb.is_pressed(self.key))
            except Exception:
                return False
        return False

    def sleep(self, seconds: float) -> None:
        """Сон, который прерывается сразу после нажатия стоп-клавиши."""
        deadline = time.monotonic() + seconds
        while not self.triggered():
            left = deadline - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(0.05, left))


def iter_sends(settings: Settings, stopper: Stopper, dry_run: bool = False):
    """Генератор событий отправки.

    События:
      ("start",)        — начали (буфер сохранён, стоп-хоткей активен)
      ("sent", i)       — отправлено i-е сообщение
      ("stopped", i)    — остановлено стоп-клавишей перед i-м сообщением
      ("done",)         — все сообщения отправлены

    Буфер обмена сохраняется до старта и восстанавливается в finally —
    в том числе при Ctrl+C (генератор нужно закрыть через gen.close()).
    """
    if not dry_run:
        pyperclip = _load("pyperclip")
        kb = _load("keyboard")
        hotkey = settings.paste_hotkey or paste_hotkey_for_platform()
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = None  # например, на Linux нет xclip/xsel
    else:
        old_clipboard = None

    yield ("start",)
    try:
        if dry_run:
            # Репетиция: имитируем тайминги, но не трогаем буфер и клавиатуру
            for i in range(1, settings.count + 1):
                if stopper.triggered():
                    yield ("stopped", i)
                    return
                stopper.sleep(settings.delay)
                yield ("sent", i)
            yield ("done",)
            return

        for i in range(1, settings.count + 1):
            if stopper.triggered():
                yield ("stopped", i)
                return
            pyperclip.copy(settings.text)
            stopper.sleep(0.05)  # дать ОС успеть записать буфер
            kb.press_and_release(hotkey)
            stopper.sleep(settings.paste_delay)
            kb.press_and_release(settings.send_key)
            yield ("sent", i)
            stopper.sleep(settings.delay)
        yield ("done",)
    finally:
        if not dry_run and old_clipboard is not None:
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass
