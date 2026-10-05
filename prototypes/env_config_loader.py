"""Configuration Loader with Environment Overrides."""
import os

def get_config_value(key: str, default: str = "") -> str:
    env_key = f"OMNIASSIST_{key.upper()}"
    return os.environ.get(env_key, os.environ.get(key, default))
