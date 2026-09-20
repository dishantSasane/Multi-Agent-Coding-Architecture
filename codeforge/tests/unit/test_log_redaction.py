"""API keys must never reach the log output."""

import logging

from app.utils.logging import RedactingFormatter


def _fmt(msg: str, monkeypatch) -> str:
    monkeypatch.setattr(
        "app.utils.logging.get_settings",
        lambda: type("S", (), {"llm_api_keys": {"gemini": "AQ.secretvalue123"}})(),
    )
    record = logging.LogRecord("x", logging.INFO, "f", 1, msg, None, None)
    return RedactingFormatter("%(message)s").format(record)


def test_url_key_param_is_masked(monkeypatch):
    out = _fmt("POST https://g.example/m:gen?key=abcdef123456&x=1", monkeypatch)
    assert "abcdef123456" not in out and "x=1" in out


def test_configured_key_is_masked_anywhere(monkeypatch):
    assert "AQ.secretvalue123" not in _fmt("error for AQ.secretvalue123 here", monkeypatch)
