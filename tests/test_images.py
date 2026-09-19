import requests
from PIL import Image

from anki_dict import images


def _square(path, color, size=(512, 512)):
    Image.new("RGB", size, color).save(path)
    return path


def test_watermark_strip_is_cropped():
    cropped = images.crop_watermark(Image.new("RGBA", (512, 512), "red"))
    assert cropped.size == (512, 460)     # нижние 10% срезаны
    assert cropped.mode == "RGB"


def test_collage_of_four(tmp_path):
    paths = [_square(tmp_path / f"{i}.png", c, (512, 460)) for i, c in enumerate(["red", "green", "blue", "white"])]
    out = images.create_collage(paths, tmp_path / "collage.jpg")
    with Image.open(out) as collage:
        assert collage.size == (1600, 359)
        # слоты идут слева направо в порядке картинок: первый красный, последний белый
        r, g, b = collage.getpixel((200, 100))
        assert r > 200 and g < 60 and b < 60
        assert all(channel > 200 for channel in collage.getpixel((1400, 100)))


def test_collage_shrinks_when_some_images_failed(tmp_path):
    paths = [_square(tmp_path / f"{i}.png", "red", (512, 460)) for i in range(2)]
    with Image.open(images.create_collage(paths, tmp_path / "c.jpg")) as collage:
        assert collage.size[0] == 800


def test_clean_definition():
    raw = "(of a person) never thinking about things that are serious (= important); also shallow:"
    assert images.clean_definition(raw) == "never thinking about things that are serious"


def test_scenes_from_real_answer(llm_json):
    scenes = images.parse_scenes(llm_json("scenes")["choices"][0]["message"]["content"])
    assert len(scenes) == 4
    assert all(len(s) > 15 for s in scenes)


def test_prompts_fall_back_to_templates_on_empty_answer(monkeypatch, capsys):
    monkeypatch.setattr(images, "ask_llm", lambda *a, **kw: "")
    prompts = images.build_prompts("womb", "the organ:", "A baby in the womb.")
    assert len(prompts) == 4 and all(images.STYLE in p for p in prompts)
    assert "пустой ответ" in capsys.readouterr().out


def test_prompts_fall_back_to_templates_on_network_error(monkeypatch):
    def boom(*a, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(images, "ask_llm", boom)
    assert len(images.build_prompts("womb", "the organ:", "")) == 4


class _Resp:
    def __init__(self, status_code, content=b""):
        self.status_code, self.content = status_code, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")


def _png_bytes():
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (512, 512), "green").save(buf, format="PNG")
    return buf.getvalue()


def test_prohibitions_go_to_negative_prompt_not_into_the_prompt():
    # Stable Diffusion отрицаний не понимает: «no nudity» в промпте для неё — слово «nudity»
    assert "nud" not in images.STYLE.lower() and " no " not in f" {images.STYLE.lower()} "
    assert "nudity" in images.NEGATIVE and "text" in images.NEGATIVE


def test_get_image_retries_and_crops(monkeypatch, tmp_path, capsys):
    urls, answers = [], [_Resp(500), _Resp(200, _png_bytes())]
    monkeypatch.setattr(images.http, "get", lambda url, **kw: urls.append(url) or answers.pop(0))
    monkeypatch.setattr(images.time, "sleep", lambda s: None)

    assert images.get_image("a clerk, stamping", tmp_path / "1.png", token=None, seed=1) is True
    with Image.open(tmp_path / "1.png") as saved:
        assert saved.size == (512, 460)
    assert "negative_prompt=nudity" in urls[0] and "seed=1" in urls[0]
    assert "попытка 1/3 (500 Server Error)" in capsys.readouterr().out


def test_get_image_gives_up_quietly(monkeypatch, tmp_path):
    monkeypatch.setattr(images.http, "get", lambda url, **kw: _Resp(500))
    monkeypatch.setattr(images.time, "sleep", lambda s: None)
    assert images.get_image("p", tmp_path / "1.png", token="secret-token", seed=2) is False
    assert not (tmp_path / "1.png").exists()


def test_no_images_means_no_collage(monkeypatch, tmp_path):
    monkeypatch.setattr(images, "build_prompts", lambda *a, **kw: ["p1", "p2"])
    monkeypatch.setattr(images, "get_image", lambda *a, **kw: False)
    monkeypatch.setattr(images.time, "sleep", lambda s: None)
    assert images.create_image_collage(tmp_path, "come over", "def", "ex") is None


def test_collage_file_name_and_cleanup(monkeypatch, tmp_path):
    def fake_get_image(prompt, out_path, token, seed):
        if seed == 2:             # одна из картинок не получилась
            return False
        _square(out_path, "blue", (512, 460))
        return True

    monkeypatch.setattr(images, "build_prompts", lambda *a, **kw: ["p1", "p2", "p3"])
    monkeypatch.setattr(images, "get_image", fake_get_image)
    monkeypatch.setattr(images.time, "sleep", lambda s: None)

    path = images.create_image_collage(tmp_path, "come over", "def", "ex")
    assert path.name == "collage_come_over.jpg"
    with Image.open(path) as collage:
        assert collage.size[0] == 800
    # временные картинки удачных слотов убраны — в медиа колоды лишнее не попадёт
    assert not list(tmp_path.glob("_come_over1.png")) and not list(tmp_path.glob("_come_over3.png"))
