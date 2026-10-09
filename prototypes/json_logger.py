"""Structured JSON Logger."""
import json
import time

def log_event(level: str, event_type: str, data: dict) -> str:
    payload = {
        "timestamp": time.time(),
        "level": level,
        "event_type": event_type,
        "data": data
    }
    return json.dumps(payload)
