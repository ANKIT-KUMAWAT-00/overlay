"""API Key Validation Helper."""

def is_valid_gemini_key(key: str) -> bool:
    if not key or len(key) < 30:
        return False
    return key.startswith("AIzaSy")
