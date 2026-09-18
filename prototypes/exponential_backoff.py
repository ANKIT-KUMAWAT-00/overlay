"""Bounded Exponential Backoff with Jitter."""
import random

def calculate_backoff(attempt: int, base: float = 0.5, max_delay: float = 8.0) -> float:
    exp_delay = base * (2 ** attempt)
    capped = min(exp_delay, max_delay)
    jitter = random.uniform(0.8, 1.2)
    return capped * jitter
