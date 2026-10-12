"""TG-MSG — командная оболочка: интерактивный мастер + флаги (typer + rich)."""
import sys
import time
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from . import __version__
from .banner import print_banner
from .config import load_config, save_config
from .core import (
    SPEED_DELAYS,
    Settings,
    Speed,
    Stopper,
    iter_sends,
    paste_hotkey_for_platform,
)

app = typer.Typer(
    add_completion=False,
    help="Вставляет текст в активное поле ввода N раз и жмёт Enter.\n\n"
    "Без флагов запускается интерактивный мастер — просто жми Enter.",
)
console = Console()

BUILTIN = {
    "count": 10,
    "delay": 0.4,
    "paste_delay": 0.15,
    "prepare": 5.0,
    "stop_key": "esc",
    "send_key": "enter",
}

SPEED_LABELS = {
    "slow": "медленно · 1 с",
    "normal": "обычно · 0.4 с",
    "fast": "быстро · 0.2 с",
    "max": "максимум · 0.08 с",
}
SPEED_MENU = [("1", "slow"), ("2", "normal"), ("3", "fast"), ("4", "max")]
SPEED_KEY_BY_CHOICE = dict(SPEED_MENU)
SPEED_CHOICE_BY_KEY = {v: k for k, v in SPEED_MENU}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"tgmsg {__version__}")
        raise typer.Exit()


def _num(value, fallback):
    """Число из конфига или фолбэк (конфиг мог быть испорчен руками)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _wizard(cfg: dict, p: dict) -> dict:
    """Спрашивает только то, что не задано флагами. Enter = значение по умолчанию."""
    console.print(
        Panel(
            "Заполни параметры — [bold]Enter принимает значение в [скобках][/bold]",
            title="Мастер запуска",
            expand=False,
            border_style="bright_blue",
            padding=(0, 2),
        )
    )
    if p["text"] is None:
        p["text"] = Prompt.ask(
            "  Текст сообщения", default=cfg.get("text") or "пися попа кака"
        )
    if p["delay"] is None and p["speed"] is None:
        default_choice = SPEED_CHOICE_BY_KEY.get(cfg.get("speed") or "", "2")
        choice = Prompt.ask(
            "  Скорость:  [1] медленно  [2] обычно  [3] быстро  [4] максимум",
            choices=list(SPEED_KEY_BY_CHOICE),
            default=default_choice,
            show_choices=False,
        )
        p["speed"] = SPEED_KEY_BY_CHOICE[choice]
    if p["count"] is None:
        p["count"] = IntPrompt.ask(
            "  Сколько сообщений", default=int(_num(cfg.get("count"), BUILTIN["count"]))
        )
    if p["send_key"] is None:
        by_ctrl = Confirm.ask(
            "  Отправлять по Ctrl+Enter?", default=cfg.get("send_key") == "ctrl+enter"
        )
        p["send_key"] = "ctrl+enter" if by_ctrl else "enter"
    if p["prepare"] is None:
        p["prepare"] = IntPrompt.ask(
            "  Секунд на переключение в окно",
            default=int(_num(cfg.get("prepare"), BUILTIN["prepare"])),
        )
    return p


def _speed_display(speed: Optional[str], delay: float) -> str:
    if speed in SPEED_DELAYS and abs(delay - SPEED_DELAYS[Speed(speed)]) < 1e-9:
        return SPEED_LABELS[speed]
    return f"своя · {delay:g} с"


def _settings_table(s: Settings, speed_label: str, dry_run: bool) -> Table:
    table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2, 0, 0))
    table.add_column(style="dim", justify="right", no_wrap=True)
    table.add_column()
    table.add_row("текст", repr(s.text))
    table.add_row("сообщений", str(s.count))
    table.add_row("скорость", speed_label)
    table.add_row("пауза перед Enter", f"{s.paste_delay:g} с")
    table.add_row("клавиши", f"вставка: {s.paste_hotkey or paste_hotkey_for_platform()} · отправка: {s.send_key}")
    table.add_row("стоп-клавиша", s.stop_key)
    table.add_row(
        "режим",
        "[yellow]DRY-RUN — ничего не отправляется[/yellow]" if dry_run else "боевой",
    )
    return table


def _countdown(seconds: float, stopper: Stopper) -> bool:
    """Цветной отсчёт: чем ближе старт, тем «горячее» цвет. False = отмена."""
    if seconds <= 0:
        return True
    for s in range(int(seconds), 0, -1):
        if stopper.triggered():
            return False
        style = "bold red" if s <= 3 else ("bold yellow" if s <= 6 else "bold cyan")
        line = Text(f"{s:2d} с — переключись в поле ввода!  Esc — отмена", style=style)
        line.pad_right(60)
        console.print(line, end="\r")
        time.sleep(1)
    if stopper.triggered():
        return False
    console.print(Text("Поехали!".ljust(60), style="bold green"))
    return True


def _result_panel(sent: int, total: int, elapsed: float, stopped: bool, dry_run: bool) -> None:
    if stopped:
        body, border = f"Остановлено после {sent} из {total}  ·  {elapsed:.1f} с", "yellow"
    elif dry_run:
        body, border = f"Репетиция окончена: отправили бы {sent}  ·  {elapsed:.1f} с", "green"
    else:
        body, border = f"Готово! Отправлено {sent} из {total}  ·  {elapsed:.1f} с", "green"
    console.print(
        Panel(Text(body, style="bold", justify="center"), expand=False, border_style=border)
    )


@app.command()
def main(
    text: Optional[str] = typer.Option(
        None, "--text", "-t", help="Текст сообщений. Не задан — мастер спросит."
    ),
    count: Optional[int] = typer.Option(
        None, "--count", "-n", min=1, help="Сколько раз отправить."
    ),
    speed: Optional[Speed] = typer.Option(
        None, "--speed", help="Пресет скорости — пауза между сообщениями."
    ),
    delay: Optional[float] = typer.Option(
        None, "--delay", min=0.0, help="Точная пауза после каждой отправки, с (важнее --speed)."
    ),
    paste_delay: Optional[float] = typer.Option(
        None, "--paste-delay", min=0.0, help="Пауза между вставкой и Enter, с."
    ),
    prepare: Optional[float] = typer.Option(
        None, "--prepare", min=0.0, help="Отсчёт до старта — время переключиться в окно."
    ),
    stop_key: Optional[str] = typer.Option(
        None, "--stop-key", help="Клавиша аварийной остановки."
    ),
    send_key: Optional[str] = typer.Option(
        None, "--send-key", help="enter или ctrl+enter (если такая отправка в Telegram)."
    ),
    paste_hotkey: Optional[str] = typer.Option(
        None, "--paste-hotkey", help="Переопределить вставку (авто: ctrl+v / cmd+v)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Репетиция: тайминги как в бою, но ничего не отправляется."
    ),
    no_save: bool = typer.Option(
        False, "--no-save", help="Не запоминать эти настройки в ~/.tgmsg.json."
    ),
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Версия и выход."
    ),
) -> None:
    """Подготовиться, отсчитать время и отправить текст N раз в активное окно."""
    try:
        _run(text, count, speed, delay, paste_delay, prepare, stop_key, send_key,
             paste_hotkey, dry_run, no_save)
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано.[/yellow]")
        raise typer.Exit(130)


def _run(text, count, speed, delay, paste_delay, prepare, stop_key, send_key,
         paste_hotkey, dry_run, no_save) -> None:
    print_banner(console, __version__)
    cfg = load_config()

    passed = {
        "text": text,
        "count": count,
        "speed": speed.value if speed is not None else None,
        "delay": delay,
        "paste_delay": paste_delay,
        "prepare": prepare,
        "stop_key": stop_key,
        "send_key": send_key,
        "paste_hotkey": paste_hotkey,
    }

    interactive = passed["text"] is None
    if interactive:
        if not sys.stdin.isatty():
            console.print(
                "[red]Нет интерактивного терминала — передай хотя бы --text[/red] [dim](справка: --help)[/dim]"
            )
            raise typer.Exit(2)
        passed = _wizard(cfg, passed)

    # ── Разрешение значений: флаг > конфиг > встроенный дефолт ──────────
    r_text = (passed["text"] or "").strip()
    if not r_text:
        console.print("[red]Пустой текст — отправлять нечего.[/red]")
        raise typer.Exit(2)

    r_speed = passed.get("speed")
    if r_speed is not None and r_speed not in SPEED_DELAYS:
        r_speed = None
    r_delay = passed.get("delay")
    if r_delay is None and r_speed is None:
        r_delay = _num(cfg.get("delay"), None)
        r_speed = cfg.get("speed") if cfg.get("speed") in SPEED_DELAYS else "normal"
    if r_delay is None:
        r_delay = SPEED_DELAYS[Speed(r_speed)] if r_speed else BUILTIN["delay"]

    r_count = max(1, int(_num(passed.get("count"), _num(cfg.get("count"), BUILTIN["count"]))))
    r_paste_delay = _num(passed.get("paste_delay"), _num(cfg.get("paste_delay"), BUILTIN["paste_delay"]))
    r_prepare = _num(passed.get("prepare"), _num(cfg.get("prepare"), BUILTIN["prepare"]))
    r_stop_key = passed.get("stop_key") or cfg.get("stop_key") or BUILTIN["stop_key"]
    r_send_key = passed.get("send_key") or cfg.get("send_key") or BUILTIN["send_key"]
    if r_send_key not in ("enter", "ctrl+enter"):
        console.print("[red]send_key должен быть enter или ctrl+enter[/red] [dim](проверь конфиг/флаг)[/dim]")
        raise typer.Exit(2)
    r_paste_hotkey = passed.get("paste_hotkey") or cfg.get("paste_hotkey") or None

    settings = Settings(
        text=r_text, count=r_count, delay=r_delay, paste_delay=r_paste_delay,
        prepare=r_prepare, stop_key=r_stop_key, send_key=r_send_key,
        paste_hotkey=r_paste_hotkey,
    )
    speed_label = _speed_display(r_speed, r_delay)

    # ── Запоминаем настройки на следующий раз ───────────────────────────
    preset_match = r_speed in SPEED_DELAYS and abs(r_delay - SPEED_DELAYS[Speed(r_speed)]) < 1e-9
    if not no_save:
        path = save_config({
            "text": r_text,
            "count": r_count,
            "speed": r_speed,
            "delay": None if preset_match else r_delay,
            "paste_delay": r_paste_delay,
            "prepare": r_prepare,
            "stop_key": r_stop_key,
            "send_key": r_send_key,
            "paste_hotkey": r_paste_hotkey,
        })
        if path:
            console.print(f"[dim]настройки сохранены в {path}[/dim]")

    console.print(
        Panel(
            _settings_table(settings, speed_label, dry_run),
            title="Настройки",
            expand=False,
            border_style="bright_blue",
            padding=(0, 1),
        )
    )

    if interactive and not Confirm.ask("Стартуем?", default=True):
        console.print("[dim]Отменено.[/dim]")
        raise typer.Exit(0)

    # ── Стоп-клавиша активна ещё до отсчёта ─────────────────────────────
    stopper = Stopper(r_stop_key, enabled=not dry_run)
    try:
        error = stopper.activate()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    if error:
        console.print(
            f"[yellow]Хоткей «{r_stop_key}» не зарегистрировался ({error}).\n"
            f"  Остановка — только Ctrl+C в терминале.[/yellow]"
        )

    if dry_run:
        console.print("[dim]dry-run: отсчёт пропущен, начинаем репетицию[/dim]\n")
    else:
        console.print("Кликни в поле ввода получателя!")
        if not _countdown(r_prepare, stopper):
            console.print("\n[yellow]Отменено во время отсчёта.[/yellow]")
            raise typer.Exit(1)

    stopped_at = None
    started = time.monotonic()
    events = iter_sends(settings, stopper, dry_run=dry_run)
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=28),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("отправка", total=settings.count)
            for event in events:
                if event[0] == "sent":
                    progress.advance(task)
                elif event[0] == "stopped":
                    stopped_at = event[1]
    except KeyboardInterrupt:
        events.close()  # внутри генератора восстановится буфер обмена
        console.print("\n[yellow]Прервано (Ctrl+C). Буфер обмена восстановлен.[/yellow]")
        raise typer.Exit(130)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    elapsed = time.monotonic() - started
    sent = stopped_at - 1 if stopped_at else settings.count
    if not dry_run and not stopped_at:
        console.print("[dim]буфер обмена восстановлен[/dim]")
    _result_panel(sent, settings.count, elapsed, stopped=bool(stopped_at), dry_run=dry_run)


if __name__ == "__main__":
    app()
