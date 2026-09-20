"""Safari AppleScript Bridge."""
import subprocess

def get_safari_active_url() -> str:
    script = 'tell application "Safari" to return URL of current tab of front window'
    try:
        out = subprocess.check_output(["osascript", "-e", script], text=True).strip()
        return out
    except Exception:
        return ""
