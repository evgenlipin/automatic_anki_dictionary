"""Единственный вход в сеть: ретраи и одна SSL-политика на весь прогон."""
import time

import requests
import urllib3
from colorama import Fore, Style
from fake_useragent import UserAgent

REQUEST_TIMEOUT = 10   # сек на один запрос
MAX_RETRIES = 3        # попыток при сетевой ошибке
RETRY_BACKOFF = 2      # сек, линейный рост паузы между попытками

_headers = {"User-Agent": UserAgent().random}   # один на весь прогон
_verify = True   # при первой SSL-ошибке (корп-MITM прокси) выключается на весь прогон


def request(method, url, *, retries=MAX_RETRIES, timeout=REQUEST_TIMEOUT, headers=None, quiet=False, **kwargs):
    """HTTP-запрос с ретраями на сетевых ошибках; после `retries` пробрасывает исключение.

    За корпоративным MITM-прокси проверка сертификата падает — при первой SSLError отключаем
    verify на весь прогон (тянем публичные страницы и картинки) и повторяем сразу, не тратя попытку.
    Статус ответа здесь не проверяется: 404 у словаря — это ответ, а не сбой.
    """
    global _verify
    last_exc = None
    attempt = 1
    while attempt <= retries:
        try:
            return requests.request(
                method, url, timeout=timeout, headers={**_headers, **(headers or {})},
                verify=_verify, **kwargs,
            )
        except requests.exceptions.SSLError as exc:
            # только провал проверки сертификата: разовый обрыв handshake — обычный сетевой сбой,
            # из-за него снимать проверку на весь прогон (и слать токен без неё) нельзя
            if _verify and "CERTIFICATE_VERIFY_FAILED" in str(exc):
                _verify = False
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                print(f"  {Fore.YELLOW}SSL verify off (корпоративный MITM-прокси){Style.RESET_ALL}")
                continue
            last_exc = exc
        except requests.RequestException as exc:
            last_exc = exc
        if not quiet:
            print(f"  {Fore.YELLOW}network retry {attempt}/{retries}: {type(last_exc).__name__}{Style.RESET_ALL}")
        if attempt < retries:
            time.sleep(RETRY_BACKOFF * attempt)
        attempt += 1
    raise last_exc


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)


def download(url, path):
    """Скачать файл. Не-200 — HTTPError: иначе тело ошибки сохранилось бы как `word.mp3`."""
    resp = get(url)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
