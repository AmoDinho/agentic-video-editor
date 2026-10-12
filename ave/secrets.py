from __future__ import annotations

import os

SERVICE = "ave-video-editor"

try:
    import keyring
except Exception:
    keyring = None


def get_api_key(provider: str, env_name: str | None = None) -> str | None:
    if env_name:
        val = os.environ.get(env_name)
        if val:
            return val
    defaults = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openai_compatible": "OPENAI_API_KEY",
    }
    env = os.environ.get(defaults.get(provider, ""))
    if env:
        return env
    if keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE, provider)
    except Exception:
        return None


def set_api_key(provider: str, key: str) -> None:
    if keyring is None:
        raise RuntimeError("keyring is not available")
    keyring.set_password(SERVICE, provider, key)


def delete_api_key(provider: str) -> None:
    if keyring is None:
        return
    try:
        keyring.delete_password(SERVICE, provider)
    except Exception:
        pass


def has_api_key(provider: str, env_name: str | None = None) -> bool:
    return bool(get_api_key(provider, env_name))
