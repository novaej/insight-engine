from unittest.mock import MagicMock, patch

from insight_engine.adapters.mailgun_email import MailgunEmailProvider


def test_send_builds_request():
    provider = MailgunEmailProvider("key", "mg.example.com", "alerts@example.com")
    with patch("insight_engine.adapters.mailgun_email.requests.post") as mock_post:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        ok = provider.send("to@example.com", "Subject", "body", "<p>body</p>")

    assert ok is True
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.mailgun.net/v3/mg.example.com/messages"
    assert kwargs["auth"] == ("api", "key")
    assert kwargs["data"]["to"] == "to@example.com"
    assert kwargs["data"]["from"] == "alerts@example.com"
    assert kwargs["data"]["html"] == "<p>body</p>"


def test_send_returns_false_when_unconfigured():
    provider = MailgunEmailProvider("", "", "")
    assert provider.send("to@example.com", "s", "b") is False


def test_send_returns_false_on_error():
    provider = MailgunEmailProvider("key", "mg.example.com", "alerts@example.com")
    with patch("insight_engine.adapters.mailgun_email.requests.post", side_effect=Exception("boom")):
        assert provider.send("to@example.com", "s", "b") is False
