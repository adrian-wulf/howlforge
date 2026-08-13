"""Telegram bot: capture ideas from your phone.

Features:
* Optional owner whitelist (``TELEGRAM_CHAT_ID`` / ``TELEGRAM_CHAT_IDS``).
* Reply-keyboard menu with a guided flow:
    Add idea -> (project) -> category -> type the note
    New project -> type the name
    New category -> type name and subcategories
    Project -> set a default project (every idea then goes to it)
    Language -> toggle PL/EN
* The chosen language and default project are persisted per user in the vault
  (``.howlforge/bot_state.json``), so they survive restarts.
* Free-text messages are auto-routed (AI classify if possible, else manual) and
  assigned to the default project when one is set.

Run with::

    howlforge-bot          # polling
    python -m howlforge.bot
"""

from __future__ import annotations

import logging
from typing import Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from . import bot_state
from . import categories as categories_mod
from .capture import CaptureError, capture, capture_manual, reply_text
from .config import Settings, get_settings
from .i18n import normalize_lang
from .vault import create_project, delete_note, delete_project, list_notes, list_projects

logger = logging.getLogger(__name__)

router = Router()

# Transient per-chat flow state (current step / chosen project / chosen category).
_flows: Dict[int, Dict[str, object]] = {}


def _allowed_ids(settings: Settings) -> set[str]:
    ids: set[str] = set()
    if settings.telegram_chat_id.strip():
        ids.add(settings.telegram_chat_id.strip())
    for part in settings.telegram_chat_ids.split(","):
        part = part.strip()
        if part:
            ids.add(part)
    return ids


def _is_allowed(message: Message, settings: Settings) -> bool:
    allowed = _allowed_ids(settings)
    if not allowed:
        return True
    return str(message.chat.id) in allowed or str(message.from_user.id) in allowed


def _lang(message: Message, settings: Settings) -> str:
    default = normalize_lang(settings.language)
    return bot_state.lang_of(settings.vault_path, message.chat.id, default)


def _default_project(message: Message, settings: Settings) -> str | None:
    return bot_state.project_of(settings.vault_path, message.chat.id)


def _set_flow(message: Message, **kwargs: object) -> None:
    _flows.setdefault(message.chat.id, {}).update(kwargs)


def _clear_flow(message: Message) -> None:
    _flows.pop(message.chat.id, None)


def _L(lang: str, en: str, pl: str) -> str:
    return en if lang == "en" else pl


def _parse_newcat(text: str) -> tuple[str, list[str], str]:
    """Parse 'Name sub1,sub2 | description' -> (name, subs, description)."""
    description = ""
    if "|" in text:
        text, description = text.split("|", 1)
    text = text.strip()
    parts = text.split(None, 1)
    name = parts[0]
    subs = parts[1].split(",") if len(parts) > 1 else []
    return name, subs, description.strip()


def _menu(lang: str) -> ReplyKeyboardMarkup:
    labels = (
        [
            ["Add idea", "New project"],
            ["New category", "Project"],
            ["Language", "Help"],
            ["Delete"],
        ]
        if lang == "en"
        else [
            ["Dodaj pomysł", "Nowy projekt"],
            ["Nowa kategoria", "Projekt"],
            ["Język", "Pomoc"],
            ["Usuń"],
        ]
    )
    kb = [[KeyboardButton(text=t) for t in row] for row in labels]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def _project_menu(
    projects: list[str], lang: str, with_no_project: bool = True
) -> ReplyKeyboardMarkup:
    no_project = _L(lang, "No project", "Brak projektu")
    cancel = _L(lang, "Cancel", "Anuluj")
    rows = [[KeyboardButton(text=p)] for p in projects]
    if with_no_project:
        rows.append([KeyboardButton(text=no_project)])
    rows.append([KeyboardButton(text=cancel)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _category_menu(categories: list[str], lang: str) -> ReplyKeyboardMarkup:
    auto = "Auto (AI)"
    cancel = _L(lang, "Cancel", "Anuluj")
    rows = []
    for i in range(0, len(categories), 2):
        row = [KeyboardButton(text=categories[i])]
        if i + 1 < len(categories):
            row.append(KeyboardButton(text=categories[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=auto)])
    rows.append([KeyboardButton(text=cancel)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _delete_type_menu(lang: str) -> ReplyKeyboardMarkup:
    del_project = _L(lang, "Delete project", "Usuń projekt")
    del_category = _L(lang, "Delete category", "Usuń kategorię")
    del_note = _L(lang, "Delete note", "Usuń notatkę")
    cancel = _L(lang, "Cancel", "Anuluj")
    kb = [
        [KeyboardButton(text=del_project), KeyboardButton(text=del_category)],
        [KeyboardButton(text=del_note)],
        [KeyboardButton(text=cancel)],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def _items_menu(items: list[str], lang: str) -> ReplyKeyboardMarkup:
    cancel = _L(lang, "Cancel", "Anuluj")
    rows = [[KeyboardButton(text=i)] for i in items]
    rows.append([KeyboardButton(text=cancel)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _recent_notes(settings: Settings, limit: int = 20) -> list[tuple[str, str]]:
    """Return (title, relative_path) for the most recent notes."""
    from .schema import Note

    items: list[tuple[str, str]] = []
    for p in list_notes(settings.vault_path):
        try:
            note = Note.from_markdown(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        items.append((note.title, str(p.relative_to(settings.vault_path))))
    items.sort(key=lambda t: t[1])
    return items[:limit]


def _help_text(lang: str) -> str:
    if lang == "en":
        return (
            "HowlForge\n"
            "Send any thought and I'll classify and save it.\n"
            "Buttons: Add idea / New project / New category / Project / Language.\n"
            "Commands: /help, /lang, /newcat Name sub1,sub2 | description, /cancel"
        )
    return (
        "HowlForge\n"
        "Wyślij dowolną myśl, a ja ją sklasyfikuję i zapiszę.\n"
        "Przyciski: Dodaj pomysł / Nowy projekt / Nowa kategoria / Projekt / Język.\n"
        "Komendy: /help, /lang, /newcat Nazwa pod1,pod2 | opis, /cancel"
    )


def _current_status(message: Message, settings: Settings) -> str:
    lang = _lang(message, settings)
    project = _default_project(message, settings)
    if lang == "en":
        return f"Language: {lang} | Default project: {project or 'none'}"
    return f"Język: {lang} | Domyślny projekt: {project or 'brak'}"


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    _clear_flow(message)
    await message.answer(
        _help_text(_lang(message, settings)), reply_markup=_menu(_lang(message, settings))
    )


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    await message.answer(
        _help_text(_lang(message, settings)), reply_markup=_menu(_lang(message, settings))
    )


@router.message(Command("status"))
async def on_status(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    await message.answer(_current_status(message, settings))


@router.message(Command("cancel"))
async def on_cancel(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    _clear_flow(message)
    await message.answer(
        _help_text(_lang(message, settings)), reply_markup=_menu(_lang(message, settings))
    )


@router.message(Command("lang"))
async def on_lang(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    await message.answer(f"Language: {_lang(message, settings)}")


@router.message(Command("newcat"))
async def on_newcat(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    text = (message.text or "").removeprefix("/newcat").strip()
    lang = _lang(message, settings)
    if not text:
        usage = _L(
            lang,
            "Usage: /newcat CategoryName sub1,sub2 | short description",
            "Użycie: /newcat NazwaKategorii pod1,pod2 | krótki opis",
        )
        await message.answer(usage)
        return
    name, subs, description = _parse_newcat(text)
    try:
        slug = categories_mod.add(settings.vault_path, name, subs, description=description)
    except ValueError as exc:
        await message.answer(f"Could not add category: {exc}")
        return
    done = _L(_lang(message, settings), "Added category", "Dodano kategorię")
    await message.answer(f"{done}: {slug}")


@router.message(F.text)
async def on_text(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    lang = _lang(message, settings)
    text = (message.text or "").strip()

    add_idea = _L(lang, "Add idea", "Dodaj pomysł")
    new_project = _L(lang, "New project", "Nowy projekt")
    new_category = _L(lang, "New category", "Nowa kategoria")
    project_btn = _L(lang, "Project", "Projekt")
    help_ = _L(lang, "Help", "Pomoc")
    lang_btn = _L(lang, "Language", "Język")
    cancel = _L(lang, "Cancel", "Anuluj")
    no_project = _L(lang, "No project", "Brak projektu")
    delete_btn = _L(lang, "Delete", "Usuń")
    del_project = _L(lang, "Delete project", "Usuń projekt")
    del_category = _L(lang, "Delete category", "Usuń kategorię")
    del_note = _L(lang, "Delete note", "Usuń notatkę")

    # --- Main menu buttons -------------------------------------------------
    if text == add_idea:
        default = _default_project(message, settings)
        if default:
            _set_flow(message, step="pick_category", project=default)
            cats = list(categories_mod.all_categories(settings.vault_path))
            prompt = _L(lang, "Pick a category:", "Wybierz kategorię:")
            await message.answer(prompt, reply_markup=_category_menu(cats, lang))
        else:
            projects = list_projects(settings.vault_path)
            _set_flow(message, step="pick_project")
            prompt = _L(lang, "Pick a project:", "Wybierz projekt:")
            await message.answer(prompt, reply_markup=_project_menu(projects, lang))
        return
    if text == new_project:
        _set_flow(message, step="await_project")
        prompt = _L(lang, "Send the project name:", "Podaj nazwę projektu:")
        await message.answer(prompt)
        return
    if text == new_category:
        _set_flow(message, step="await_category")
        prompt = _L(
            lang,
            "Send the category name, optional subcategories and an optional "
            "description: Name sub1,sub2 | description",
            "Podaj nazwę kategorii, opcjonalne podkategorie i opcjonalny opis: "
            "Nazwa pod1,pod2 | opis",
        )
        await message.answer(prompt)
        return
    if text == project_btn:
        projects = list_projects(settings.vault_path)
        _set_flow(message, step="pick_default_project")
        prompt = _L(lang, "Pick your default project:", "Wybierz domyślny projekt:")
        await message.answer(prompt, reply_markup=_project_menu(projects, lang))
        return
    if text == help_:
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return
    if text == lang_btn:
        new = "en" if lang == "pl" else "pl"
        bot_state.set_user(settings.vault_path, message.chat.id, lang=new)
        await message.answer(
            _current_status(message, settings), reply_markup=_menu(new)
        )
        return
    if text == delete_btn:
        _set_flow(message, step="pick_delete")
        prompt = _L(lang, "What do you want to delete?", "Co chcesz usunąć?")
        await message.answer(prompt, reply_markup=_delete_type_menu(lang))
        return
    if text == cancel:
        _clear_flow(message)
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return

    flow = _flows.get(message.chat.id)

    # --- Guided: pick delete type ------------------------------------------
    if flow and flow.get("step") == "pick_delete":
        if text == del_project:
            _set_flow(message, step="del_project")
            await message.answer(
                _L(lang, "Pick a project to delete:", "Wybierz projekt do usunięcia:"),
                reply_markup=_items_menu(list_projects(settings.vault_path), lang),
            )
        elif text == del_category:
            custom = list(categories_mod.load(settings.vault_path))
            _set_flow(message, step="del_category")
            await message.answer(
                _L(lang, "Pick a category to delete:", "Wybierz kategorię do usunięcia:"),
                reply_markup=_items_menu(custom, lang),
            )
        elif text == del_note:
            _set_flow(message, step="del_note")
            titles = [t for t, _ in _recent_notes(settings)]
            await message.answer(
                _L(lang, "Pick a note to delete:", "Wybierz notatkę do usunięcia:"),
                reply_markup=_items_menu(titles, lang),
            )
        else:
            await message.answer(
                _L(lang, "Unknown option, pick again.", "Nieznana opcja, wybierz ponownie.")
            )
        return

    # --- Guided: delete project --------------------------------------------
    if flow and flow.get("step") == "del_project":
        count = delete_project(settings.vault_path, text)
        _clear_flow(message)
        done = _L(lang, "Deleted project", "Usunięto projekt")
        await message.answer(f"{done}: {text} ({count} notes)", reply_markup=_menu(lang))
        return

    # --- Guided: delete category -------------------------------------------
    if flow and flow.get("step") == "del_category":
        try:
            removed = categories_mod.remove(settings.vault_path, text)
        except ValueError as exc:
            await message.answer(f"{_L(lang, 'Problem', 'Problem')}: {exc}")
            return
        _clear_flow(message)
        if removed:
            done = _L(lang, "Deleted category", "Usunięto kategorię")
        else:
            done = _L(lang, "Not found", "Nie znaleziono")
        await message.answer(f"{done}: {text}", reply_markup=_menu(lang))
        return

    # --- Guided: delete note -----------------------------------------------
    if flow and flow.get("step") == "del_note":
        target = None
        for title, rel in _recent_notes(settings, limit=100):
            if title == text:
                target = rel
                break
        if target is None:
            await message.answer(_L(lang, "Note not found.", "Nie znaleziono notatki."))
            return
        delete_note(settings.vault_path, target)
        _clear_flow(message)
        done = _L(lang, "Deleted note", "Usunięto notatkę")
        await message.answer(f"{done}: {text}", reply_markup=_menu(lang))
        return

    # --- Guided: pick project (for a single idea) --------------------------
    if flow and flow.get("step") == "pick_project":
        projects = list_projects(settings.vault_path)
        if text == no_project:
            _set_flow(message, step="pick_category", project=None)
        elif text in projects:
            _set_flow(message, step="pick_category", project=text)
        else:
            await message.answer(
                _L(lang, "Unknown project, pick again.", "Nieznany projekt, wybierz ponownie.")
            )
            return
        cats = list(categories_mod.all_categories(settings.vault_path))
        prompt = _L(lang, "Pick a category:", "Wybierz kategorię:")
        await message.answer(prompt, reply_markup=_category_menu(cats, lang))
        return

    # --- Guided: pick default project (persistent) -------------------------
    if flow and flow.get("step") == "pick_default_project":
        projects = list_projects(settings.vault_path)
        if text == no_project:
            bot_state.set_user(settings.vault_path, message.chat.id, project="")
        elif text in projects:
            bot_state.set_user(settings.vault_path, message.chat.id, project=text)
        else:
            await message.answer(
                _L(lang, "Unknown project, pick again.", "Nieznany projekt, wybierz ponownie.")
            )
            return
        _clear_flow(message)
        await message.answer(_current_status(message, settings), reply_markup=_menu(lang))
        return

    # --- Guided: pick category ---------------------------------------------
    if flow and flow.get("step") == "pick_category":
        if text == "Auto (AI)":
            _set_flow(message, step="await_idea", category=None)
        else:
            cats = categories_mod.all_categories(settings.vault_path)
            chosen = text.lower()
            if chosen not in cats:
                await message.answer(
                    _L(
                        lang,
                        "Unknown category, pick again.",
                        "Nieznana kategoria, wybierz ponownie.",
                    )
                )
                return
            _set_flow(message, step="await_idea", category=chosen)
        prompt = _L(lang, "Now send the idea text.", "Teraz napisz treść pomysłu.")
        await message.answer(prompt)
        return

    # --- Guided: awaiting idea text ----------------------------------------
    if flow and flow.get("step") == "await_idea":
        category = flow.get("category")
        project = flow.get("project") or _default_project(message, settings)
        try:
            if category:
                result = capture_manual(
                    text,
                    settings,
                    project=str(project) if project else None,
                    category=str(category),
                )
            else:
                result = capture(text, settings, project=str(project) if project else None)
        except CaptureError as exc:
            await message.answer(f"{_L(lang, 'Problem', 'Problem')}: {exc}")
            return
        _clear_flow(message)
        await message.answer(reply_text(result, lang), reply_markup=_menu(lang))
        return

    # --- Guided: awaiting project name -------------------------------------
    if flow and flow.get("step") == "await_project":
        try:
            slug = create_project(settings.vault_path, text)
        except ValueError as exc:
            await message.answer(f"{_L(lang, 'Problem', 'Problem')}: {exc}")
            return
        _clear_flow(message)
        done = _L(lang, "Created project", "Utworzono projekt")
        await message.answer(f"{done}: {slug}", reply_markup=_menu(lang))
        return

    # --- Guided: awaiting new category -------------------------------------
    if flow and flow.get("step") == "await_category":
        name, subs, description = _parse_newcat(text)
        try:
            slug = categories_mod.add(settings.vault_path, name, subs, description=description)
        except ValueError as exc:
            await message.answer(f"{_L(lang, 'Could not add', 'Nie udało się dodać')}: {exc}")
            return
        _clear_flow(message)
        done = _L(lang, "Added category", "Dodano kategorię")
        await message.answer(f"{done}: {slug}", reply_markup=_menu(lang))
        return

    # --- Free text: auto-route (assigned to default project) ---------------
    project = _default_project(message, settings)
    try:
        result = capture(text, settings, project=project)
    except CaptureError:
        try:
            result = capture_manual(text, settings, project=project)
        except CaptureError as exc:
            await message.answer(f"{_L(lang, 'Problem', 'Problem')}: {exc}")
            return
    await message.answer(reply_text(result, lang), reply_markup=_menu(lang))


async def _main() -> None:
    import asyncio

    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot is idle (no polling).")
        while True:
            await asyncio.sleep(3600)
    bot = Bot(
        settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("HowlForge bot starting in polling mode...")
    await dp.start_polling(bot, skip_updates=True)


def main() -> None:
    """Sync entry point for the ``howlforge-bot`` console script."""
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
