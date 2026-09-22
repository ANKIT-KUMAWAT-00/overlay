"""IDE Detection Logic."""

def identify_ide(process_name: str) -> str:
    p = process_name.lower()
    if "code" in p:
        return "vscode"
    if any(jb in p for jb in ["pycharm", "idea", "clion", "webstorm"]):
        return "jetbrains"
    return "generic"
