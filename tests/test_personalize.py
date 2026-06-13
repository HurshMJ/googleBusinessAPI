from src.models import Business, read_leads, write_leads
from src.personalize import build_prompt, personalize_business, personalize_csv


class FakeBlock:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeBlock(text)]


class FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeMessage(self._text)


class FakeClient:
    def __init__(self, text):
        self.messages = FakeMessages(text)


def _biz(name="Joe's Tacos"):
    return Business(
        name=name,
        primary_type="restaurant",
        formatted_address="1 Main St, Austin, TX",
        place_id="p1",
    )


def test_build_prompt_includes_name_category_location():
    prompt = build_prompt(_biz())
    assert "Joe's Tacos" in prompt
    assert "restaurant" in prompt
    assert "Austin" in prompt


def test_build_prompt_falls_back_to_types_for_category():
    b = Business(name="X", types=["bakery"], place_id="p")
    assert "bakery" in build_prompt(b)


def test_personalize_business_parses_subject_and_body():
    client = FakeClient("Subject: Hi Joe\nLet's build your site.")
    subject, body = personalize_business(_biz(), client=client, model="m")
    assert subject == "Hi Joe"
    assert body == "Let's build your site."
    assert client.messages.calls[0]["model"] == "m"


def test_personalize_business_subject_fallback():
    client = FakeClient("No subject line here, just body.")
    subject, body = personalize_business(_biz(), client=client)
    assert "Joe's Tacos" in subject  # fallback uses the name
    assert body


def test_personalize_csv_fills_columns(tmp_path):
    path = tmp_path / "leads.csv"
    write_leads(path, [_biz("A"), _biz("B")])
    client = FakeClient("Subject: Hello\nBody text.")
    drafted = personalize_csv(path, client=client)
    assert drafted == 2
    rows = read_leads(path)
    assert all(r.subject == "Hello" and r.body == "Body text." for r in rows)


def test_personalize_csv_skips_failing_row(tmp_path):
    path = tmp_path / "leads.csv"
    write_leads(path, [_biz("A"), _biz("B")])

    class FlakyMessages:
        def __init__(self):
            self.n = 0

        def create(self, **kwargs):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("boom")
            return FakeMessage("Subject: Hi\nBody.")

    class FlakyClient:
        def __init__(self):
            self.messages = FlakyMessages()

    drafted = personalize_csv(path, client=FlakyClient())
    assert drafted == 1  # one failed, batch continued
