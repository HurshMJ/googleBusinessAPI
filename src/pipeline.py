"""Orchestrate discover -> draft."""

from __future__ import annotations

import logging

from . import discover as discover_mod
from . import personalize as personalize_mod

log = logging.getLogger(__name__)


def run(
    query: str,
    csv_path,
    *,
    location: tuple[float, float] | None = None,
    radius_m: float | None = None,
    max_pages: int = 3,
    model: str | None = None,
) -> dict:
    """Discover no-website businesses, then draft personalized emails."""
    businesses, added = discover_mod.discover_to_csv(
        query,
        csv_path,
        location=location,
        radius_m=radius_m,
        max_pages=max_pages,
    )
    drafted = personalize_mod.personalize_csv(csv_path, model=model)
    log.info(
        "pipeline: discovered %d (%d new), drafted %d",
        len(businesses),
        added,
        drafted,
    )
    return {"discovered": len(businesses), "added": added, "drafted": drafted}
