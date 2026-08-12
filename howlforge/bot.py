"""Telegram bot: capture ideas from your phone.

Features:
* Optional owner whitelist (``TELEGRAM_CHAT_ID`` / ``TELEGRAM_CHAT_IDS``).
* Reply-keyboard menu and a guided flow:
    Add idea -> pick project -> pick category -> type the note
    New project -> type the name
    New category -> type name and subcategories
* Free-text messages are auto-routed (AI classify if possible, else manual).

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

from . import categories as categories_mod
from .capture import CaptureError, capture, capture_manual, reply_text
from .config import Settings, get_settings
from .i18n import normalize_lang
from .vault import create_project, list_projects

logger = logging.getLogger(__name__)

router = Router()

# Per-chat flow state: chat_id -> {"step", "project", "category", "lang"}
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


def _lang(message: Message) -> str:
    flow = _flows.get(message.chat.id)
    if flow and flow.get("lang"):
        return str(flow["lang"])
    return normalize_lang(get_settings().language)


def _set_flow(message: Message, **kwargs: object) -> None:
    flow = _flows.setdefault(message.chat.id, {})
    flow.update(kwargs)
    flow.setdefault("lang", normalize_lang(get_settings().language))


def _clear_flow(message: Message) -> None:
    _flows.pop(message.chat.id, None)


def _L(lang: str, en: str, pl: str) -> str:
    return en if lang == "en" else pl


def _menu(lang: str) -> ReplyKeyboardMarkup:
    labels = (
        [["Add idea", "New project"], ["New category", "Language"], ["Help"]]
        if lang == "en"
        else [["Dodaj pomysł", "Nowy projekt"], ["Nowa kategoria", "Język"], ["Pomoc"]]
    )
    kb = [[KeyboardButton(text=t) for t in row] for row in labels]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def _project_menu(projects: list[str], lang: str) -> ReplyKeyboardMarkup:
    no_project = _L(lang, "No project", "Brak projektu")
    cancel = _L(lang, "Cancel", "Anuluj")
    rows = [[KeyboardButton(text=p)] for p in projects]
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


def _help_text(lang: str) -> str:
    if lang == "en":
        return (
            "HowlForge\n"
            "Send any thought and I'll classify and save it.\n"
            "Buttons: Add idea / New project / New category.\n"
            "Commands: /help, /lang, /newcat Name sub1,sub2, /cancel"
        )
    return (
        "HowlForge\n"
        "Wyślij dowolną myśl, a ja ją sklasyfikuję i zapiszę.\n"
        "Przyciski: Dodaj pomysł / Nowy projekt / Nowa kategoria.\n"
        "Komendy: /help, /lang, /newcat Nazwa pod1,pod2, /cancel"
    )


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    _clear_flow(message)
    await message.answer(_help_text(_lang(message)), reply_markup=_menu(_lang(message)))


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    if not _is_allowed(message, get_settings()):
        return
    await message.answer(_help_text(_lang(message)), reply_markup=_menu(_lang(message)))


@router.message(Command("cancel"))
async def on_cancel(message: Message) -> None:
    if not _is_allowed(message, get_settings()):
        return
    _clear_flow(message)
    await message.answer(_help_text(_lang(message)), reply_markup=_menu(_lang(message)))


@router.message(Command("lang"))
async def on_lang(message: Message) -> None:
    if not _is_allowed(message, get_settings()):
        return
    lang = _lang(message)
    await message.answer(f"Language: {lang}")


@router.message(Command("newcat"))
async def on_newcat(message: Message) -> None:
    if not _is_allowed(message, get_settings()):
        return
    settings = get_settings()
    text = (message.text or "").removeprefix("/newcat").strip()
    if not text:
        await message.answer("Usage: /newcat CategoryName sub1,sub2")
        return
    parts = text.split(None, 1)
    name = parts[0]
    subs = parts[1].split(",") if len(parts) > 1 else []
    try:
        slug = categories_mod.add(settings.vault_path, name, subs)
    except ValueError as exc:
        await message.answer(f"Could not add category: {exc}")
        return
    done = _L(_lang(message), "Added category", "Dodano kategorię")
    await message.answer(f"{done}: {slug}")


@router.message(F.text)
async def on_text(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    lang = _lang(message)
    text = (message.text or "").strip()

    add_idea = _L(lang, "Add idea", "Dodaj pomysł")
    new_project = _L(lang, "New project", "Nowy projekt")
    new_category = _L(lang, "New category", "Nowa kategoria")
    help_ = _L(lang, "Help", "Pomoc")
    lang_btn = _L(lang, "Language", "Język")
    cancel = _L(lang, "Cancel", "Anuluj")
    no_project = _L(lang, "No project", "Brak projektu")

    # --- Main menu buttons -------------------------------------------------
    if text == add_idea:
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
            "Send the category name and optional subcategories: Name sub1,sub2",
            "Podaj nazwę kategorii i opcjonalnie podkategorie: Nazwa pod1,pod2",
        )
        await message.answer(prompt)
        return
    if text == help_:
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return
    if text == lang_btn:
        new = "en" if lang == "pl" else "pl"
        _set_flow(message, lang=new)
        await message.answer(f"Language: {new}", reply_markup=_menu(new))
        return
    if text == cancel:
        _clear_flow(message)
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return

    flow = _flows.get(message.chat.id)

    # --- Guided: pick project ----------------------------------------------
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
        prompt = _L(
            lang,
            "Now send the idea text.",
            "Teraz napisz treść pomysłu.",
        )
        await message.answer(prompt)
        return

    # --- Guided: awaiting idea text ----------------------------------------
    if flow and flow.get("step") == "await_idea":
        category = flow.get("category")
        project = flow.get("project")
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
        parts = text.split(None, 1)
        name = parts[0]
        subs = parts[1].split(",") if len(parts) > 1 else []
        try:
            slug = categories_mod.add(settings.vault_path, name, subs)
        except ValueError as exc:
            await message.answer(f"{_L(lang, 'Could not add', 'Nie udało się dodać')}: {exc}")
            return
        _clear_flow(message)
        done = _L(lang, "Added category", "Dodano kategorię")
        await message.answer(f"{done}: {slug}", reply_markup=_menu(lang))
        return

    # --- Free text: auto-route ---------------------------------------------
    try:
        result = capture(text, settings)
    except CaptureError:
        try:
            result = capture_manual(text, settings)
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
