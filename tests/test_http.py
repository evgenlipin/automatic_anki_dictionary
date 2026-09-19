import pytest
import requests

from anki_dict import http


class _Resp:
    def __init__(self, status_code=200, content=b"ok"):
        self.status_code, self.content = status_code, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def net(monkeypatch):
    """Подменить requests.request сценарием: исключение — бросить, иначе — вернуть. Запоминает verify."""
    def install(*script):
        queue, seen = list(script), []

        def fake(method, url, **kwargs):
            seen.append(kwargs["verify"])
            step = queue.pop(0)
            if isinstance(step, Exception):
                raise step
            return step

        monkeypatch.setattr(http.requests, "request", fake)
        monkeypatch.setattr(http.time, "sleep", lambda s: None)
        monkeypatch.setattr(http, "_verify", True)
        return seen
    return install


def test_retries_then_succeeds(net):
    seen = net(requests.ConnectionError("x"), requests.Timeout("y"), _Resp())
    assert http.get("https://x", quiet=True).status_code == 200
    assert len(seen) == 3


def test_gives_up_with_last_exception(net):
    seen = net(requests.ConnectionError("1"), requests.ConnectionError("2"), requests.Timeout("3"))
    with pytest.raises(requests.Timeout):
        http.get("https://x", quiet=True)
    assert len(seen) == 3


def test_status_is_not_checked_here(net):
    net(_Resp(404))
    assert http.get("https://x").status_code == 404     # 404 у словаря — ответ, а не сбой


def test_certificate_failure_turns_verification_off_without_spending_attempts(net, capsys):
    cert = requests.exceptions.SSLError("[SSL: CERTIFICATE_VERIFY_FAILED] Missing Authority Key Identifier")
    seen = net(cert, _Resp(), _Resp())
    assert http.get("https://x", retries=1).status_code == 200   # retries=1, а запрос всё равно повторён
    http.get("https://y")
    assert seen == [True, False, False]                          # выключено до конца прогона
    assert "SSL verify off" in capsys.readouterr().out


def test_other_ssl_errors_do_not_turn_verification_off(net):
    # разовый обрыв handshake — обычный сетевой сбой: снимать проверку (и слать токен без неё) нельзя
    seen = net(requests.exceptions.SSLError("EOF occurred in violation of protocol"), _Resp())
    assert http.get("https://x", quiet=True).status_code == 200
    assert seen == [True, True]


def test_download_writes_file(net, tmp_path):
    net(_Resp(200, b"mp3-bytes"))
    http.download("https://x/a.mp3", tmp_path / "a.mp3")
    assert (tmp_path / "a.mp3").read_bytes() == b"mp3-bytes"


def test_download_error_page_is_not_saved_as_mp3(net, tmp_path):
    net(_Resp(403, b"<html>Forbidden</html>"))
    with pytest.raises(requests.HTTPError):
        http.download("https://x/a.mp3", tmp_path / "a.mp3")
    assert not (tmp_path / "a.mp3").exists()
