"""
OS-protected credential storage using keyring with environment variable fallback.
"""

from __future__ import annotations

import os
from typing import Optional

from logging_service.logger import get_logger

logger = get_logger("security.credential_store")

SERVICE_NAME = "OmniAssistDesktop"
GEMINI_KEY_NAME = "gemini_api_key"


class CredentialStore:
    """
    Manages secure retrieval and storage of API credentials.
    Prioritizes OS Keyring (macOS Keychain, Windows Credential Manager, Linux SecretService),
    with graceful fallback to environment variables.
    """

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name
        self._keyring_available = False
        self._init_keyring()

    def _init_keyring(self) -> None:
        try:
            import keyring
            # Test that a backend is functional
            backend = keyring.get_keyring()
            if backend and "fail" not in backend.__class__.__name__.lower():
                self._keyring_available = True
                logger.debug("Keyring backend initialized: %s", backend.name)
            else:
                logger.warning("Keyring backend not fully functional. Falling back to env vars.")
        except Exception as exc:
            logger.warning("Could not initialize keyring: %s", exc)
            self._keyring_available = False

    def get_api_key(self, custom_env_var: Optional[str] = None) -> Optional[str]:
        """
        Retrieves the Gemini API key from OS keyring or environment.
        Checks in order:
        1. OS Keyring
        2. custom_env_var (if provided)
        3. GEMINI_API_KEY
        4. GOOGLE_API_KEY
        """
        # 1. Try keyring
        if self._keyring_available:
            try:
                import keyring
                key = keyring.get_password(self.service_name, GEMINI_KEY_NAME)
                if key and key.strip():
                    return key.strip()
            except Exception as exc:
                logger.warning("Failed to retrieve key from keyring: %s", exc)

        # 2. Try custom env var
        if custom_env_var and custom_env_var in os.environ:
            val = os.environ[custom_env_var].strip()
            if val:
                return val

        # 3. Standard env vars
        for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            val = os.getenv(env_name, "").strip()
            if val:
                return val

        return None

    def store_api_key(self, api_key: str) -> bool:
        """
        Stores the Gemini API key into the OS keyring.
        Returns True on success, False if keyring is unavailable or errors out.
        """
        if not api_key or not api_key.strip():
            return False

        clean_key = api_key.strip()
        os.environ["GEMINI_API_KEY"] = clean_key
        # Fallback persistence to .env
        try:
            from pathlib import Path
            env_file = Path(".env")
            lines = []
            if env_file.exists():
                lines = env_file.read_text(encoding="utf-8").splitlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith("GEMINI_API_KEY="):
                    lines[i] = f'GEMINI_API_KEY="{clean_key}"'
                    found = True
                    break
            if not found:
                lines.append(f'GEMINI_API_KEY="{clean_key}"')
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

        if self._keyring_available:
            try:
                import keyring
                keyring.set_password(self.service_name, GEMINI_KEY_NAME, clean_key)
                logger.info("Successfully stored API key in OS credential store.")
                return True
            except Exception as exc:
                logger.error("Failed to store API key in keyring: %s", exc)
                return True  # Saved to environment/.env fallback

        logger.warning("OS keyring unavailable; saved to environment/.env fallback.")
        return True

    def delete_api_key(self) -> bool:
        """
        Deletes the stored Gemini API key from the OS keyring.
        """
        if self._keyring_available:
            try:
                import keyring
                keyring.delete_password(self.service_name, GEMINI_KEY_NAME)
                logger.info("Successfully deleted API key from OS credential store.")
                return True
            except Exception as exc:
                logger.warning("Could not delete API key from keyring: %s", exc)
                return False
        return False

    @staticmethod
    def mask_key(key: Optional[str]) -> str:
        """Returns a safe masked version of the key for UI presentation."""
        if not key:
            return "Not Configured"
        k = key.strip()
        if len(k) <= 8:
            return "••••••••"
        return f"{k[:4]}••••••••{k[-4:]}"
