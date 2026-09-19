"""Словари. У каждого: parse(сырой ответ) без сети и lookup(word) с сетью.

Оба возвращают Entry, BaseRef (словоформа → базовое слово) или None (слова нет).
"""
import requests


def word_exists(resp):
    """True — 200, разбираем; False — 404, слова нет; всё остальное — сбой, а не «слова нет».

    403 (бан по UA/IP), 429, 5xx → HTTPError: строка остаётся в words.txt на ретрай. Иначе при
    заблокированном Cambridge все слова молча уехали бы в Wiktionary и вышли без звука и IPA.
    """
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise requests.HTTPError(f"{resp.status_code} от {resp.url.split('/')[2]}", response=resp)
