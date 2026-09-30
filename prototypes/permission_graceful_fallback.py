"""Graceful Permission Fallback Handler."""

def prompt_accessibility_permission_dialog() -> bool:
    print("Accessibility permissions missing. Displaying guidance modal.")
    return False
