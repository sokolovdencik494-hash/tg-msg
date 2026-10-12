"""ASCII-баннер TG-MSG (шрифт ANSI Shadow) с цветным градиентом."""
from rich.console import Console
from rich.text import Text

_T = ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "]
_G = [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "]
_M = ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"]
_S = ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"]

LOGO_ROWS = ["  ".join(cols) for cols in zip(_T, _G, _M, _S, _G)]
ROW_STYLES = [
    "bold bright_cyan",
    "bold bright_cyan",
    "bold bright_blue",
    "bold blue",
    "bold magenta",
    "bold bright_magenta",
]


def print_banner(console: Console, version: str) -> None:
    for row, style in zip(LOGO_ROWS, ROW_STYLES):
        console.print(Text(row, style=style))
    console.print(
        Text(
            f"v{version}  ·  by rezonator  ·  Esc — стоп  ·  Ctrl+C — выход",
            style="dim",
        )
    )
    console.print()
