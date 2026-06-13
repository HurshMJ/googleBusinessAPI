from src import discover as discover_mod
from src.discover import discover, discover_to_csv
from src.models import read_leads


class FakeResp:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._data


class FakeSession:
    """Records calls and returns queued page payloads."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return FakeResp(self.pages[len(self.calls) - 1])


def _place(pid, name, website=None):
    p = {
        "id": pid,
        "displayName": {"text": name},
        "primaryType": "plumber",
        "types": ["plumber"],
        "formattedAddress": "1 Main St",
        "location": {"latitude": 30.0, "longitude": -97.0},
        "nationalPhoneNumber": "(512) 555-0100",
    }
    if website:
        p["websiteUri"] = website
    return p


def test_filters_out_businesses_with_website():
    session = FakeSession(
        [
            {
                "places": [
                    _place("a", "No Site Plumbing"),
                    _place("b", "Has Site Plumbing", website="https://b.example"),
                ]
            }
        ]
    )
    out = discover("plumbers", api_key="fake", max_pages=1, session=session)
    assert [b.place_id for b in out] == ["a"]
    assert out[0].name == "No Site Plumbing"
    assert out[0].national_phone == "(512) 555-0100"
    assert out[0].lat == 30.0


def test_field_mask_header_sent():
    session = FakeSession([{"places": []}])
    discover("plumbers", api_key="fake", max_pages=1, session=session)
    headers = session.calls[0]["headers"]
    assert "X-Goog-FieldMask" in headers
    assert headers["X-Goog-Api-Key"] == "fake"
    assert "places.websiteUri" in headers["X-Goog-FieldMask"]


def test_pagination_follows_next_page_token(monkeypatch):
    monkeypatch.setattr(discover_mod.time, "sleep", lambda *_: None)
    session = FakeSession(
        [
            {"places": [_place("a", "One")], "nextPageToken": "tok"},
            {"places": [_place("b", "Two")]},
        ]
    )
    out = discover("plumbers", api_key="fake", max_pages=3, session=session)
    assert [b.place_id for b in out] == ["a", "b"]
    assert session.calls[1]["json"]["pageToken"] == "tok"


def test_error_status_raises_without_leaking_key():
    class ErrSession:
        def post(self, *a, **k):
            return FakeResp({}, status_code=403)

    try:
        discover("plumbers", api_key="secret", max_pages=1, session=ErrSession())
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "secret" not in str(exc)


def test_discover_to_csv_writes_no_website_rows(tmp_path):
    path = tmp_path / "leads.csv"
    session = FakeSession(
        [{"places": [_place("a", "No Site"), _place("b", "Site", website="https://x")]}]
    )
    found, added = discover_to_csv(
        "plumbers", path, api_key="fake", max_pages=1, session=session
    )
    assert added == 1
    rows = read_leads(path)
    assert [r.place_id for r in rows] == ["a"]
    assert rows[0].email == ""
