from src.models import Business, append_leads, read_leads, write_leads


def _sample(place_id="p1", name="Joe's Tacos", website=""):
    return Business(
        name=name,
        primary_type="restaurant",
        types=["restaurant", "food"],
        formatted_address="1 Main St, Austin, TX",
        lat=30.27,
        lng=-97.74,
        national_phone="(512) 555-0100",
        place_id=place_id,
        website_uri=website,
    )


def test_row_roundtrip():
    b = _sample()
    restored = Business.from_row(b.to_row())
    assert restored.name == b.name
    assert restored.types == b.types
    assert restored.lat == b.lat
    assert restored.place_id == b.place_id
    assert restored.email == ""


def test_write_then_read(tmp_path):
    path = tmp_path / "leads.csv"
    write_leads(path, [_sample("p1"), _sample("p2", name="Bar")])
    rows = read_leads(path)
    assert [r.place_id for r in rows] == ["p1", "p2"]
    assert rows[0].lat == 30.27


def test_append_dedupes_by_place_id(tmp_path):
    path = tmp_path / "leads.csv"
    assert append_leads(path, [_sample("p1"), _sample("p2")]) == 2
    # p1 already present -> only p3 is new
    added = append_leads(path, [_sample("p1"), _sample("p3")])
    assert added == 1
    assert {r.place_id for r in read_leads(path)} == {"p1", "p2", "p3"}


def test_read_missing_file_returns_empty(tmp_path):
    assert read_leads(tmp_path / "nope.csv") == []
