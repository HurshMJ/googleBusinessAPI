"""Environment configuration.

Importing this module never raises, so it is safe to import in CI without any
keys set. The ``require_*`` accessors raise :class:`ConfigError` only when a
value that a specific step actually needs is missing.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing."""


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Sending is OFF by default. Real sends require an explicit DRY_RUN=false.
DRY_RUN = _bool("DRY_RUN", True)
RATE_LIMIT = float(os.getenv("RATE_LIMIT", "1.0"))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "")
FROM_NAME = os.getenv("FROM_NAME", "")

# CAN-SPAM required outbound elements.
SENDER_POSTAL_ADDRESS = os.getenv("SENDER_POSTAL_ADDRESS", "")
UNSUBSCRIBE_URL = os.getenv("UNSUBSCRIBE_URL", "")


def require_google_key() -> str:
    if not GOOGLE_MAPS_API_KEY:
        raise ConfigError("GOOGLE_MAPS_API_KEY is not set. See .env.example.")
    return GOOGLE_MAPS_API_KEY


def require_anthropic_key() -> str:
    if not ANTHROPIC_API_KEY:
        raise ConfigError("ANTHROPIC_API_KEY is not set. See .env.example.")
    return ANTHROPIC_API_KEY


def require_smtp() -> None:
    missing = [
        name
        for name, value in {
            "SMTP_HOST": SMTP_HOST,
            "SMTP_USER": SMTP_USER,
            "SMTP_PASSWORD": SMTP_PASSWORD,
            "FROM_EMAIL": FROM_EMAIL,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing SMTP config: " + ", ".join(missing) + ". See .env.example."
        )


def require_compliance() -> None:
    missing = [
        name
        for name, value in {
            "SENDER_POSTAL_ADDRESS": SENDER_POSTAL_ADDRESS,
            "UNSUBSCRIBE_URL": UNSUBSCRIBE_URL,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing CAN-SPAM footer config: "
            + ", ".join(missing)
            + ". A physical postal address and unsubscribe link are legally required."
        )
