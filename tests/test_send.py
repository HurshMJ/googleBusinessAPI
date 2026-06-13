import src.send as send_mod
from src.models import Business, write_leads
from src.send import (
    build_footer,
    is_deceptive_subject,
    read_suppression,
    send_pipeline,
)


class FakeSMTP:
    def __init__(self):
        self.sent = []

    def send_message(self, msg):
        self.sent.append(msg)


def _lead(email="", name="A", subject="Hello there", body="Hi.", pid="p"):
    return Business(name=name, email=email, subject=subject, body=body, place_id=pid)


def _set_compliance(monkeypatch):
    # Env gate must also be open for a real send (double gate).
    monkeypatch.setattr(send_mod.config, "DRY_RUN", False)
    monkeypatch.setattr(send_mod.config, "SENDER_POSTAL_ADDRESS", "1 Main St, TX")
    monkeypatch.setattr(send_mod.config, "UNSUBSCRIBE_URL", "https://x.example/u")
    monkeypatch.setattr(send_mod.config, "FROM_EMAIL", "me@example.com")
    monkeypatch.setattr(send_mod.config, "FROM_NAME", "Me")


def test_is_deceptive_subject():
    assert is_deceptive_subject("")
    assert is_deceptive_subject("Re: your account")
    assert is_deceptive_subject("FREE MONEY NOW!!!")
    assert not is_deceptive_subject("A quick idea for your shop")


def test_read_suppression(tmp_path):
    path = tmp_path / "supp.csv"
    path.write_text("email\nBad@Example.com\n\nignore@x.com\n")
    out = read_suppression(path)
    assert out == {"bad@example.com", "ignore@x.com"}


def test_dry_run_sends_nothing(tmp_path, capsys):
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    write_leads(leads, [_lead(email="owner@shop.com")])
    fake = FakeSMTP()
    stats = send_pipeline(leads, supp, dry_run=True, smtp=fake)
    assert stats["sent"] == 0
    assert fake.sent == []
    assert "[DRY-RUN]" in capsys.readouterr().out


def test_skips_empty_email(tmp_path):
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    write_leads(leads, [_lead(email=""), _lead(email="ok@shop.com", pid="p2")])
    fake = FakeSMTP()
    stats = send_pipeline(leads, supp, dry_run=True, smtp=fake)
    assert stats["skipped_empty"] == 1


def test_real_send_appends_footer_and_honors_suppression(tmp_path, monkeypatch):
    _set_compliance(monkeypatch)
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    supp.write_text("email\nblocked@shop.com\n")
    write_leads(
        leads,
        [
            _lead(email="owner@shop.com", pid="p1"),
            _lead(email="blocked@shop.com", pid="p2"),
        ],
    )
    fake = FakeSMTP()
    stats = send_pipeline(leads, supp, dry_run=False, rate_limit=0, smtp=fake)

    assert stats["sent"] == 1
    assert stats["skipped_suppressed"] == 1
    assert len(fake.sent) == 1
    assert fake.sent[0]["To"] == "owner@shop.com"
    body = fake.sent[0].get_content()
    assert "1 Main St, TX" in body  # physical address
    assert "Unsubscribe: https://x.example/u" in body


def test_blocks_deceptive_subject(tmp_path, monkeypatch):
    _set_compliance(monkeypatch)
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    write_leads(leads, [_lead(email="owner@shop.com", subject="Re: invoice")])
    fake = FakeSMTP()
    stats = send_pipeline(leads, supp, dry_run=False, rate_limit=0, smtp=fake)
    assert stats["skipped_subject"] == 1
    assert fake.sent == []


def test_rate_limit_sleeps_between_sends(tmp_path, monkeypatch):
    _set_compliance(monkeypatch)
    calls = []
    monkeypatch.setattr(send_mod.time, "sleep", lambda s: calls.append(s))
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    write_leads(
        leads,
        [
            _lead(email="a@shop.com", pid="p1"),
            _lead(email="b@shop.com", pid="p2"),
        ],
    )
    send_pipeline(leads, supp, dry_run=False, rate_limit=1.5, smtp=FakeSMTP())
    assert calls == [1.5]  # slept once, between the two sends


def test_real_send_blocked_when_env_dry_run_true(tmp_path, monkeypatch):
    # CLI --no-dry-run alone must not be enough; env DRY_RUN must also be false.
    monkeypatch.setattr(send_mod.config, "DRY_RUN", True)
    leads = tmp_path / "leads.csv"
    supp = tmp_path / "supp.csv"
    write_leads(leads, [_lead(email="owner@shop.com")])
    fake = FakeSMTP()
    try:
        send_pipeline(leads, supp, dry_run=False, rate_limit=0, smtp=fake)
        assert False, "expected ConfigError"
    except send_mod.config.ConfigError:
        pass
    assert fake.sent == []


def test_footer_contains_required_elements(monkeypatch):
    _set_compliance(monkeypatch)
    footer = build_footer()
    assert "1 Main St, TX" in footer
    assert "Unsubscribe:" in footer
