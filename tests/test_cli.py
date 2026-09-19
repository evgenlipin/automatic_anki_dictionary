from anki_dict import cli, deck
from anki_dict.models import Card


def test_default_command_is_run(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(cli, "run_batch", lambda ws, pipeline: seen.update(ws=ws, pipeline=pipeline))
    assert cli.main(["--workspace", str(tmp_path)]) == 0
    assert seen["ws"] == tmp_path
    assert seen["pipeline"].make_collage is not None


def test_no_images_flag(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(cli, "run_batch", lambda ws, pipeline: seen.update(pipeline=pipeline))
    cli.main(["run", "--no-images", "--workspace", str(tmp_path)])
    assert seen["pipeline"].make_collage is None


def test_inspect_missing_file(tmp_path, capsys):
    assert cli.main(["inspect", "--workspace", str(tmp_path)]) == 1
    assert "нет файла" in capsys.readouterr().out


def test_inspect_relative_path_is_inside_workspace(tmp_path, capsys):
    backups = tmp_path / "apkg_backups"
    backups.mkdir()
    card = Card(word="womb", pos="noun", ipa="", definition="d", examples=["A.", "B."], source="cambridge")
    deck.write_package([card], backups / "old.apkg", tmp_path / "unused")

    assert cli.main(["inspect", "apkg_backups/old.apkg", "--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "заметок: 1" in out and "ex=2" in out and "womb" in out
