"""Settings Panel Mock Spec."""

SETTINGS_SCHEMA = {
    "api_key": {"type": "secret", "label": "Gemini API Key"},
    "model_name": {"type": "choice", "options": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-flash"]},
    "auto_paste": {"type": "boolean", "default": True},
    "dark_mode": {"type": "boolean", "default": True}
}
