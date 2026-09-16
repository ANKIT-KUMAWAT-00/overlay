"""JSON Boundary Auto-Repair."""
import json
from typing import Optional

def repair_truncated_json(raw: str) -> Optional[dict]:
    clean = raw.strip()
    stack = []
    for ch in clean:
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    repaired = clean
    for unclosed in reversed(stack):
        repaired += "}" if unclosed == "{" else "]"

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None
