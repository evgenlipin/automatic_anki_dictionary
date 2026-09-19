"""Точка входа: `python -m anki_dict [run|inspect]`."""
import argparse
import os
from functools import partial
from pathlib import Path

from . import http, images, inspect_apkg, llm
from .pipeline import Pipeline, run_batch
from .sources import cambridge, wiktionary


def build_pipeline(with_images=True):
    token = os.environ.get("POLLINATIONS_TOKEN") or None   # нет токена → аноним (медленнее)
    return Pipeline(
        lookup_cambridge=cambridge.lookup,
        lookup_wiktionary=wiktionary.lookup,
        generate_examples=partial(llm.generate_examples, token=token),
        suggest_spelling=partial(llm.suggest_spelling, token=token),
        download=http.download,
        make_collage=partial(images.create_image_collage, token=token) if with_images else None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="anki_dict", description=__doc__)
    parser.add_argument("command", nargs="?", default="run", choices=["run", "inspect"],
                        help="run — собрать колоду из words.txt (по умолчанию); inspect — разобрать output.apkg")
    parser.add_argument("path", nargs="?", help="для inspect: путь к .apkg (по умолчанию output.apkg в workspace)")
    parser.add_argument("--workspace", default=os.environ.get("ANKI_WORKSPACE", "workspace"),
                        help="папка с words.txt, журналами и output.apkg")
    parser.add_argument("--no-images", action="store_true", help="без коллажей — быстрый прогон")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    if args.command == "inspect":
        # относительный путь — от workspace: `inspect apkg_backups/output-….apkg`
        return inspect_apkg.main(workspace / (args.path or "output.apkg"))

    run_batch(workspace, build_pipeline(with_images=not args.no_images))
    return 0
