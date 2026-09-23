"""Simulated Keystroke Text Injection."""
import time

def simulate_typing(text: str, delay_between_keys: float = 0.002):
    # Simulated per-key event dispatch
    for ch in text:
        time.sleep(delay_between_keys)
