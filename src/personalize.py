"""Generate personalized outreach drafts via the Claude API.

Each draft is generated per-business (no static template), referencing the
business name plus its category and/or location. Per-row failures are logged
and skipped so one bad record never aborts the batch.
"""

from __future__ import annotations

import logging

from . import config
from .models import Business, read_leads, write_leads

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You write concise, friendly B2B outreach emails to local business owners "
    "who currently have no website. You offer a short, no-pressure consultation "
    "to build one. Be specific to the business. No hype, no false or misleading "
    "claims, no spam phrasing. Output exactly two parts:\n"
    "Subject: <one short line>\n"
    "<email body>"
)

_MAX_TOKENS = 600
_TEMPERATURE = 0.4


def build_prompt(b: Business) -> str:
    """Build a per-business user prompt including name + category/location."""
    parts = [f"Business name: {b.name}"]
    category = b.primary_type or (b.types[0] if b.types else "")
    if category:
        parts.append(f"Category: {category.replace('_', ' ')}")
    if b.formatted_address:
        parts.append(f"Location: {b.formatted_address}")
    parts.append(
        "Write a personalized email (about 120-150 words) that uses the business "
        "name naturally and references its category and/or location. Invite the "
        "owner to a short call to discuss a simple website or demo."
    )
    return "\n".join(parts)


def _parse(text: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    subject = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    return subject, body


def _default_client():
    from anthropic import Anthropic

    return Anthropic(api_key=config.require_anthropic_key())


def personalize_business(
    b: Business, client=None, model: str | None = None
) -> tuple[str, str]:
    """Return (subject, body) for one business."""
    client = client or _default_client()
    model = model or config.ANTHROPIC_MODEL
    message = client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(b)}],
    )
    text = "".join(getattr(block, "text", "") for block in message.content)
    subject, body = _parse(text)
    if not subject:
        subject = f"A quick idea for {b.name}".strip()
    return subject, body


def personalize_csv(csv_path, client=None, model: str | None = None) -> int:
    """Fill subject/body for every lead in the CSV. Returns count drafted."""
    leads = read_leads(csv_path)
    client = client or _default_client()
    drafted = 0
    for b in leads:
        try:
            b.subject, b.body = personalize_business(b, client=client, model=model)
            drafted += 1
        except Exception as exc:  # noqa: BLE001 - per-row resilience by design
            log.warning("personalize failed for %s: %s", b.name or b.place_id, exc)
            continue
    write_leads(csv_path, leads)
    return drafted
