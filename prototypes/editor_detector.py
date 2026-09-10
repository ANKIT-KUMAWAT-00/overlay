"""Editor and Terminal Heuristic Detection."""
from typing import Set

KNOWN_EDITORS: Set[str] = {
    "code", "cursor", "sublime_text", "pycharm", "clion", "webstorm", "idea", "nvim", "vim", "emacs"
}

KNOWN_TERMINALS: Set[str] = {
    "iterm2", "terminal", "alacritty", "kitty", "hyper", "wezterm", "cmd.exe", "powershell.exe", "windowsterminal.exe"
}

def is_code_editor(process_name: str) -> bool:
    name = process_name.lower().replace(".exe", "")
    return name in KNOWN_EDITORS

def is_terminal(process_name: str) -> bool:
    name = process_name.lower().replace(".exe", "")
    return name in KNOWN_TERMINALS
