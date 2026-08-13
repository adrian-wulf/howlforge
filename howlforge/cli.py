"""Command-line interface for HowlForge.

Usage examples:
    howlforge init                 # bootstrap the vault folder layout
    howlforge add "an idea"        # classify + save a note (needs LLM)
    howlforge classify "an idea"   # classify and print JSON, do not save
    howlforge doctor               # show config and validate the vault
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .classify import ClassifyError, classify
from .config import get_settings
from .i18n import normalize_lang
from .llm import LLMClient, LLMError
from .vault import ensure_vault, list_notes


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="howlforge", description=__doc__)
    parser.add_argument("--version", action="version", version=f"howlforge {__version__}")
    parser.add_argument("--lang", choices=["pl", "en"], default=None,
                        help="Force output/note language (default: from env).")
    parser.add_argument("--model", default=None, help="LLM model key (default: from env).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Bootstrap the vault folder layout.")
    sub.add_parser("doctor", help="Show configuration and validate the vault.")

    add = sub.add_parser("add", help="Classify text and save it as a note.")
    add.add_argument("text", nargs="+", help="The idea text to capture.")
    add.add_argument("--print", action="store_true", dest="print_only",
                     help="Print the markdown instead of writing to disk.")

    cls = sub.add_parser("classify", help="Classify text and print the note JSON.")
    cls.add_argument("text", nargs="+", help="The idea text to classify.")

    sub.add_parser("list", help="List notes currently in the vault.")

    syn = sub.add_parser("synthesize", help="Synthesize recent notes into a digest.")
    syn.add_argument("--days", type=int, default=7, help="Look back N days (default 7).")
    syn.add_argument("--project", default=None, help="Restrict to one project slug.")

    sub.add_parser("index", help="Build the semantic search index (embed all notes).")

    srch = sub.add_parser("search", help="Semantic search over the vault.")
    srch.add_argument("query", nargs="+", help="The search query.")
    srch.add_argument("-k", type=int, default=5, help="Number of results (default 5).")

    exp = sub.add_parser("export", help="Export notes to JSON or CSV.")
    exp.add_argument("--format", choices=["json", "csv"], default="json", help="Output format.")
    exp.add_argument("--project", default=None, help="Restrict to one project slug.")
    exp.add_argument("--out", default=None, help="Output file path (default: stdout).")
    return parser


def _resolve_lang(args) -> str:
    if args.lang:
        return args.lang
    return normalize_lang(get_settings().language)


def _cmd_init(args, settings) -> int:
    root = ensure_vault(settings.vault_path)
    print(f"Vault ready at {root}")
    for p in sorted(root.iterdir()):
        if p.is_dir():
            print(f"  {p.name}/")
    return 0


def _cmd_doctor(args, settings) -> int:
    print(f"language      : {settings.language}")
    print(f"vault path    : {settings.vault_path}")
    print(f"llm model     : {settings.llm_model}")
    print(f"llm config    : {settings.llm_config}")
    print(f"telegram token: {'set' if settings.telegram_bot_token else 'not set'}")
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        print(f"llm models    : {client.available_models or '(none)'}")
    except Exception as exc:  # noqa: BLE001
        print(f"llm error     : {exc}")
    if settings.vault_path.exists():
        print(f"notes in vault: {len(list_notes(settings.vault_path))}")
    else:
        print("notes in vault: 0 (run `howlforge init`)")
    return 0


def _cmd_classify(args, settings, lang) -> int:
    text = " ".join(args.text)
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        note = classify(text, client, lang, model=args.model)
    except (LLMError, ClassifyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(note.__dict__, ensure_ascii=False, indent=2))
    return 0


def _cmd_add(args, settings, lang) -> int:
    text = " ".join(args.text)
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        note = classify(text, client, lang, model=args.model)
    except (LLMError, ClassifyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.print_only:
        print(note.to_markdown())
        return 0
    from .vault import write_note
    path = write_note(note, settings.vault_path)
    print(f"saved -> {path}")
    return 0


def _cmd_list(args, settings) -> int:
    notes = list_notes(settings.vault_path)
    if not notes:
        print("No notes yet. Run `howlforge init` then `howlforge add \"...\"`.")
        return 0
    for p in notes:
        print(p.relative_to(settings.vault_path))
    return 0


def _cmd_synthesize(args, settings, lang) -> int:
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        from .synthesize import SynthesisError, synthesize
        path = synthesize(
            settings.vault_path,
            client,
            lang,
            days=args.days,
            project=args.project,
            model=args.model,
        )
    except (LLMError, ClassifyError, SynthesisError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"synthesis saved -> {path}")
    return 0


def _cmd_index(args, settings) -> int:
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        from .search import index_vault
        count = index_vault(settings.vault_path, client)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"indexed {count} notes")
    return 0


def _cmd_search(args, settings) -> int:
    query = " ".join(args.query)
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        from .search import search
        hits = search(settings.vault_path, client, query, k=args.k)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not hits:
        print("No results.")
        return 0
    for h in hits:
        print(f"{h.score:.3f}  {h.title}  ({h.path})")
    return 0


def _cmd_export(args, settings) -> int:
    from .export import export_file, generate

    if args.out:
        path = export_file(
            settings.vault_path, Path(args.out), args.format, project=args.project
        )
        print(f"exported -> {path}")
    else:
        print(generate(settings.vault_path, args.format, project=args.project), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    # LiteLLM's per-model cost-map warnings are noise for CLI users.
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    lang = _resolve_lang(args)

    if args.command == "init":
        return _cmd_init(args, settings)
    if args.command == "doctor":
        return _cmd_doctor(args, settings)
    if args.command == "classify":
        return _cmd_classify(args, settings, lang)
    if args.command == "add":
        return _cmd_add(args, settings, lang)
    if args.command == "list":
        return _cmd_list(args, settings)
    if args.command == "synthesize":
        return _cmd_synthesize(args, settings, lang)
    if args.command == "index":
        return _cmd_index(args, settings)
    if args.command == "search":
        return _cmd_search(args, settings)
    if args.command == "export":
        return _cmd_export(args, settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
