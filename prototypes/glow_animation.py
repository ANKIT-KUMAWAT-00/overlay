"""Pulsing Glow Animation Helper."""
import math

def calculate_pulse_intensity(time_elapsed: float, period: float = 1.5) -> float:
    return 0.5 + 0.5 * math.sin(2 * math.pi * time_elapsed / period)
