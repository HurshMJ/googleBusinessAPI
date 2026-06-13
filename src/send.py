"""Guarded send pipeline.

Defaults to dry-run (prints, sends nothing). Real sends require DRY_RUN=false
AND legal sign-off (cold B2B email is regulated; see README). Always:
  - skips rows with an empty email (the expected default for this sourcing),
  - honors the suppression list,
  - blocks deceptive/empty subjects,
  - appends a CAN-SPAM footer (physical address + unsubscribe),
  - enforces a rate limit between real sends.

Transport: SMTP via the Python standard library (smtplib). Chosen over the
Gmail API to avoid an OAuth dependency; swap the transport in _send() if needed.
"""

from __future__ import annotations

import csv
import logging
import re
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from . import config
from .models import Business, read_leads

log = logging.getLogger(__name__)

# Subjects that fake a reply/forward are deceptive under CAN-SPAM.
_FAKE_THREAD = re.compile(r"^\s*(re|fwd|fw)\s*:", re.IGNORECASE)


def read_suppression(path) -> set[str]:
    """Read suppressed (do-not-contact) email addresses, lowercased."""
    p = Path(path)
    if not p.exists():
        return set()
    out: set[str] = set()
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            value = row[0].strip().lower()
            if not value or value == "email":  # skip header / blanks
                continue
            out.add(value)
    return out


def is_deceptive_subject(subject: str) -> bool:
    """True if the subject is empty or misleading (blocked from sending)."""
    s = (subject or "").strip()
    if not s:
        return True
    if _FAKE_THREAD.match(s):
        return True
    if s.isupper() and len(s) > 8:  # shouty all-caps
        return True
    return False


def build_footer() -> str:
    """CAN-SPAM footer: sender identity, physical address, unsubscribe link."""
    sender = config.FROM_NAME or config.FROM_EMAIL
    return (
        "\n\n-- \n"
        f"{sender}\n"
        f"{config.SENDER_POSTAL_ADDRESS}\n"
        f"Unsubscribe: {config.UNSUBSCRIBE_URL}"
    )


def _compose(b: Business, footer: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = b.subject
    msg["From"] = (
        f"{config.FROM_NAME} <{config.FROM_EMAIL}>"
        if config.FROM_NAME
        else config.FROM_EMAIL
    )
    msg["To"] = b.email
    msg.set_content(b.body + footer)
    return msg


def send_pipeline(
    csv_path,
    suppression_path,
    *,
    dry_run: bool | None = None,
    rate_limit: float | None = None,
    smtp=None,
) -> dict:
    """Process leads and send (or simulate sending) outreach.

    ``smtp`` lets callers/tests inject a server-like object with send_message().
    Returns a stats dict.
    """
    dry_run = config.DRY_RUN if dry_run is None else dry_run
    rate_limit = config.RATE_LIMIT if rate_limit is None else rate_limit

    leads = read_leads(csv_path)
    suppressed = read_suppression(suppression_path)
    footer = build_footer()

    stats = {
        "total": len(leads),
        "sent": 0,
        "skipped_empty": 0,
        "skipped_suppressed": 0,
        "skipped_subject": 0,
    }

    sendable: list[Business] = []
    for b in leads:
        email = (b.email or "").strip().lower()
        if not email:
            stats["skipped_empty"] += 1
            continue
        if email in suppressed:
            stats["skipped_suppressed"] += 1
            log.info("suppressed, not sending: %s", email)
            continue
        if is_deceptive_subject(b.subject):
            stats["skipped_subject"] += 1
            log.warning("blocked deceptive/empty subject for %s", email)
            continue
        sendable.append(b)

    if not dry_run:
        # Double gate: a real send requires BOTH the explicit CLI/argument
        # request (dry_run=False) AND DRY_RUN=false in the environment. This
        # keeps the legal sign-off gate from being defeated by a single flag.
        if config.DRY_RUN:
            raise config.ConfigError(
                "Real send blocked: requesting a send (dry_run=False) also "
                "requires DRY_RUN=false in the environment. Set it only after "
                "legal sign-off."
            )
        config.require_compliance()
        if smtp is None:
            config.require_smtp()
    elif not (config.SENDER_POSTAL_ADDRESS and config.UNSUBSCRIBE_URL):
        log.warning(
            "CAN-SPAM footer fields are not fully set; required before DRY_RUN=false"
        )

    owns_server = False
    server = smtp
    try:
        if not dry_run and server is None:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
            owns_server = True
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)

        for i, b in enumerate(sendable):
            msg = _compose(b, footer)
            if dry_run:
                print(f"[DRY-RUN] would send to {b.email}: {b.subject}")
                continue
            server.send_message(msg)
            stats["sent"] += 1
            log.info("sent to %s", b.email)
            if i < len(sendable) - 1 and rate_limit > 0:
                time.sleep(rate_limit)
    finally:
        if owns_server and server is not None:
            try:
                server.quit()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass

    return stats
