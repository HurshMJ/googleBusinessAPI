"""Discover businesses with no website via Google Places API (New).

Uses the Text Search endpoint. The X-Goog-FieldMask header is mandatory for
Places API (New); without it the API returns HTTP 400. Only the fields needed
for outreach are requested, to respect the Places ToS on data retention.
"""

from __future__ import annotations

import logging
import time

import requests

from . import config
from .models import Business, append_leads

log = logging.getLogger(__name__)

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.primaryType",
        "places.types",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "nextPageToken",
    ]
)

# Places requires a short delay before a nextPageToken becomes valid.
_PAGE_DELAY_S = 2.0


def _place_to_business(place: dict) -> Business:
    location = place.get("location") or {}
    return Business(
        place_id=place.get("id", ""),
        name=(place.get("displayName") or {}).get("text", ""),
        primary_type=place.get("primaryType", ""),
        types=place.get("types", []) or [],
        formatted_address=place.get("formattedAddress", ""),
        lat=location.get("latitude"),
        lng=location.get("longitude"),
        national_phone=place.get("nationalPhoneNumber", ""),
        website_uri=place.get("websiteUri", ""),
    )


def _has_no_website(b: Business) -> bool:
    return not (b.website_uri and b.website_uri.strip())


def discover(
    query: str,
    *,
    location: tuple[float, float] | None = None,
    radius_m: float | None = None,
    max_pages: int = 3,
    api_key: str | None = None,
    session=None,
) -> list[Business]:
    """Return businesses matching ``query`` that have no website.

    ``location`` is an optional (lat, lng) center; combined with ``radius_m`` it
    biases results. ``session`` lets callers/tests inject a requests-like object.
    """
    key = api_key or config.require_google_key()
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body: dict = {"textQuery": query}
    if location and radius_m:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": location[0], "longitude": location[1]},
                "radius": float(radius_m),
            }
        }

    poster = session.post if session is not None else requests.post
    results: list[Business] = []
    page_token: str | None = None

    for _ in range(max_pages):
        if page_token:
            body["pageToken"] = page_token
        try:
            resp = poster(PLACES_URL, json=body, headers=headers, timeout=30)
        except requests.RequestException as exc:
            # Never include the request headers (they carry the API key).
            raise RuntimeError(f"Places API request failed: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(
                f"Places API error {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        for place in data.get("places", []):
            business = _place_to_business(place)
            if _has_no_website(business):
                results.append(business)

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(_PAGE_DELAY_S)

    return results


def discover_to_csv(query: str, csv_path, **kwargs) -> tuple[list[Business], int]:
    """Discover and append no-website businesses to ``csv_path``.

    Returns (all_found, num_new_rows_added).
    """
    businesses = discover(query, **kwargs)
    added = append_leads(csv_path, businesses)
    log.info("found %d no-website businesses (%d new)", len(businesses), added)
    return businesses, added
