"""Data model and CSV I/O for the no-website outreach pipeline."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

# Canonical column order for leads.csv. The email column is intentionally
# present but left blank: Places API (New) does not return email addresses,
# so it is filled by a human or a future enrichment step.
CSV_FIELDS = [
    "place_id",
    "name",
    "primary_type",
    "types",
    "formatted_address",
    "lat",
    "lng",
    "national_phone",
    "email",
    "website_uri",
    "subject",
    "body",
]


@dataclass
class Business:
    """A single business lead."""

    name: str
    primary_type: str = ""
    types: list[str] = field(default_factory=list)
    formatted_address: str = ""
    lat: float | None = None
    lng: float | None = None
    national_phone: str = ""
    email: str = ""
    place_id: str = ""
    website_uri: str = ""
    subject: str = ""
    body: str = ""

    def to_row(self) -> dict:
        return {
            "place_id": self.place_id,
            "name": self.name,
            "primary_type": self.primary_type,
            "types": "|".join(self.types),
            "formatted_address": self.formatted_address,
            "lat": "" if self.lat is None else self.lat,
            "lng": "" if self.lng is None else self.lng,
            "national_phone": self.national_phone,
            "email": self.email,
            "website_uri": self.website_uri,
            "subject": self.subject,
            "body": self.body,
        }

    @classmethod
    def from_row(cls, row: dict) -> "Business":
        def _to_float(value) -> float | None:
            if value is None or value == "":
                return None
            return float(value)

        types = [t for t in (row.get("types") or "").split("|") if t]
        return cls(
            name=row.get("name", ""),
            primary_type=row.get("primary_type", ""),
            types=types,
            formatted_address=row.get("formatted_address", ""),
            lat=_to_float(row.get("lat")),
            lng=_to_float(row.get("lng")),
            national_phone=row.get("national_phone", ""),
            email=(row.get("email") or "").strip(),
            place_id=row.get("place_id", ""),
            website_uri=row.get("website_uri", ""),
            subject=row.get("subject", ""),
            body=row.get("body", ""),
        )


def read_leads(path) -> list[Business]:
    """Read all leads from a CSV. Returns [] when the file does not exist."""
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return [Business.from_row(r) for r in csv.DictReader(f)]


def write_leads(path, businesses) -> None:
    """Overwrite the CSV with header + the given businesses."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for b in businesses:
            writer.writerow(b.to_row())


def append_leads(path, businesses) -> int:
    """Append new businesses, deduping by place_id. Returns count added."""
    existing = read_leads(path)
    seen = {b.place_id for b in existing if b.place_id}
    added = []
    for b in businesses:
        if b.place_id and b.place_id in seen:
            continue
        if b.place_id:
            seen.add(b.place_id)
        added.append(b)
    write_leads(path, existing + added)
    return len(added)
