"""Разбор ответов LLM на настоящих ответах text.pollinations.ai (tests/fixtures/llm)."""
import copy

import pytest

from anki_dict import llm


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def fake_post(monkeypatch):
    """Подменить сеть: отдаёт заготовленные ответы по очереди, запоминает отправленное."""
    def install(*payloads):
        queue, sent = list(payloads), []

        def post(url, **kwargs):
            sent.append(kwargs["json"])
            return _Resp(queue.pop(0))

        monkeypatch.setattr(llm.http, "post", post)
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        return sent
    return install


def test_clean_lines_strips_numbering_and_quotes():
    text = '1. First one here.\n- "Second one here."\n\n  * Third one here.  \n2) Fourth.'
    assert llm.clean_lines(text) == ["First one here.", "Second one here.", "Third one here.", "Fourth."]


def test_generate_examples_from_real_answer(fake_post, llm_json):
    fake_post(llm_json("examples"))
    examples = llm.generate_examples("womb", "the organ…", 2)
    assert len(examples) == 2
    assert all("womb" in e.lower() for e in examples)
    assert not any(e.endswith(" ") for e in examples)   # у модели хвостовые пробелы перед переносом


def test_generate_examples_drops_chatter(fake_post, llm_json):
    payload = copy.deepcopy(llm_json("examples"))
    payload["choices"][0]["message"]["content"] = (
        "Sure! Here are your sentences:\nThe womb protects the baby.\nA womb is an organ.\nThe womb grows.")
    fake_post(payload)
    assert llm.generate_examples("womb", "", 2) == [
        "The womb protects the baby.", "A womb is an organ.", "The womb grows."]


def test_generate_examples_asks_for_one_spare(fake_post, llm_json):
    # запас на случай, когда модель повторит словарный пример и pipeline отсеет его как дубль
    sent = fake_post(llm_json("examples"))
    llm.generate_examples("womb", "", 2)
    assert "exactly 3 short" in sent[0]["messages"][0]["content"]


def test_generate_examples_keeps_inflected_forms_after_literal_ones(fake_post, llm_json):
    # раньше «She came over…» отсеивалось (нет буквального `come`), и у фразовых глаголов не добиралось до трёх
    payload = copy.deepcopy(llm_json("examples"))
    payload["choices"][0]["message"]["content"] = "She came over as shy at first.\nCome over here right now!"
    fake_post(payload)
    assert llm.generate_examples("come over", "", 2) == [
        "Come over here right now!", "She came over as shy at first."]


def test_generate_examples_splits_sentences_glued_into_one_line(fake_post, llm_json):
    # настоящий ответ из прогона 2026-09-19: просили 2 примера, пришли одной строкой
    payload = copy.deepcopy(llm_json("examples"))
    payload["choices"][0]["message"]["content"] = (
        "I misspoke when I said the capital of Australia was Sydney. "
        "She misspoke about the recipe’s salt content during the cooking demo.")
    fake_post(payload)
    assert llm.generate_examples("misspoke", "", 2) == [
        "I misspoke when I said the capital of Australia was Sydney.",
        "She misspoke about the recipe’s salt content during the cooking demo.",
    ]


def test_generate_examples_keeps_two_sentence_example_when_lines_are_enough(fake_post, llm_json):
    payload = copy.deepcopy(llm_json("examples"))
    payload["choices"][0]["message"]["content"] = "I misspoke. Sorry about that!\nShe misspoke again yesterday."
    fake_post(payload)
    assert llm.generate_examples("misspoke", "", 2)[0] == "I misspoke. Sorry about that!"


def test_empty_content_is_retried_with_low_effort(fake_post, llm_json):
    # Случай «сцены от LLM: 0/4»: модель сожгла лимит на reasoning и вернула пустой content.
    # Настоящий пустой ответ не воспроизводится по заказу, поэтому он собран из настоящего
    # ответа: в наблюдавшемся случае отличались только content ("") и completion_tokens (1500).
    empty = copy.deepcopy(llm_json("scenes"))
    empty["choices"][0]["message"]["content"] = ""
    sent = fake_post(empty, llm_json("scenes"))

    assert llm.ask_llm("prompt", effort="medium") != ""
    assert [p["reasoning_effort"] for p in sent] == ["medium", "low"]


def test_empty_content_twice_gives_empty_string(fake_post, llm_json):
    empty = copy.deepcopy(llm_json("scenes"))
    empty["choices"][0]["message"]["content"] = None
    fake_post(empty, copy.deepcopy(empty))
    assert llm.ask_llm("prompt") == ""


def test_unexpected_shape_is_value_error(fake_post):
    # KeyError уронил бы весь прогон; ValueError вызывающие ловят и идут запасным путём
    fake_post({"error": "rate limited"})
    with pytest.raises(ValueError):
        llm.ask_llm("prompt")


def test_suggest_spelling_from_real_answer(fake_post, llm_json):
    fake_post(llm_json("spelling"))
    assert llm.suggest_spelling("ignight") == "ignite"


@pytest.mark.parametrize("answer", ["?", "ignight", "I am not sure what you mean by that", "", "123"])
def test_suggest_spelling_rejects_non_answers(fake_post, llm_json, answer):
    payload = copy.deepcopy(llm_json("spelling"))
    payload["choices"][0]["message"]["content"] = answer
    fake_post(payload, copy.deepcopy(payload))
    assert llm.suggest_spelling("ignight") is None
