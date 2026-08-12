"""Telegram bot: capture ideas from your phone.

Features:
* Optional owner whitelist (``TELEGRAM_CHAT_ID`` / ``TELEGRAM_CHAT_IDS``). When set,
  only those chat/user IDs are served; everyone else is ignored.
* A reply-keyboard menu ("Dodaj pomysl", "Nowa kategoria", "Pomoc", "Jezyk") and a
  small guided flow: pick a category, then type the note.

Run with::

    howlforge-bot          # polling
    python -m howlforge.bot
"""

from __future__ import annotations

import logging
from typing import Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from . import categories as categories_mod
from .capture import CaptureError, capture, capture_manual, reply_text
from .config import Settings, get_settings
from .i18n import normalize_lang

logger = logging.getLogger(__name__)

router = Router()

# Per-chat flow state: chat_id -> {"step": str, "category": str|None, "lang": str}
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
    if "lang" not in flow:
        flow["lang"] = normalize_lang(get_settings().language)


def _clear_flow(message: Message) -> None:
    _flows.pop(message.chat.id, None)


def _menu(lang: str) -> ReplyKeyboardMarkup:
    if lang == "en":
        labels = [["Add idea", "New category"], ["Help", "Language"]]
    else:
        labels = [["Dodaj pomysł", "Nowa kategoria"], ["Pomoc", "Język"]]
    kb = [[KeyboardButton(text=t) for t in row] for row in labels]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def _category_menu(categories: list[str], lang: str) -> ReplyKeyboardMarkup:
    labels = list(categories)
    auto = "Auto (AI)"
    cancel = "Cancel" if lang == "en" else "Anuluj"
    rows = []
    for i in range(0, len(labels), 2):
        row = [KeyboardButton(text=labels[i])]
        if i + 1 < len(labels):
            row.append(KeyboardButton(text=labels[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=auto)])
    rows.append([KeyboardButton(text=cancel)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _help_text(lang: str) -> str:
    if lang == "en":
        return (
            "HowlForge\n"
            "Send any thought/idea and I'll classify and save it.\n"
            "Buttons: Add idea / New category.\n"
            "Commands: /help, /lang, /newcat Name sub1,sub2, /cancel"
        )
    return (
        "HowlForge\n"
        "Wyślij dowolną myśl/pomysł, a ja ją sklasyfikuję i zapiszę.\n"
        "Przyciski: Dodaj pomysł / Nowa kategoria.\n"
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
    done = "Added category" if _lang(message) == "en" else "Dodano kategorię"
    await message.answer(f"{done}: {slug}")


@router.message(F.text)
async def on_text(message: Message) -> None:
    settings = get_settings()
    if not _is_allowed(message, settings):
        return
    lang = _lang(message)
    text = (message.text or "").strip()

    # --- Menu buttons / flow control -------------------------------------
    add_labels = {"Dodaj pomysł", "Add idea"}
    cat_labels = {"Nowa kategoria", "New category"}
    help_labels = {"Pomoc", "Help"}
    lang_labels = {"Język", "Language"}
    cancel_labels = {"Anuluj", "Cancel"}
    auto_labels = {"Auto (AI)"}

    if text in add_labels:
        _set_flow(message, step="pick_category")
        cats = list(categories_mod.all_categories(settings.vault_path))
        prompt = "Pick a category:" if lang == "en" else "Wybierz kategorię:"
        await message.answer(prompt, reply_markup=_category_menu(cats, lang))
        return
    if text in cat_labels:
        _set_flow(message, step="await_category")
        prompt = (
            "Send the category name and optional subcategories: Name sub1,sub2"
            if lang == "en"
            else "Podaj nazwę kategorii i opcjonalnie podkategorie: Nazwa pod1,pod2"
        )
        await message.answer(prompt)
        return
    if text in help_labels:
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return
    if text in lang_labels:
        cur = _lang(message)
        new = "en" if cur == "pl" else "pl"
        _set_flow(message, lang=new)
        await message.answer(f"Language: {new}", reply_markup=_menu(new))
        return
    if text in cancel_labels:
        _clear_flow(message)
        await message.answer(_help_text(lang), reply_markup=_menu(lang))
        return

    flow = _flows.get(message.chat.id)

    # --- Guided: choose category -----------------------------------------
    if flow and flow.get("step") == "pick_category":
        if text in auto_labels:
            _set_flow(message, step="await_idea", category=None)
            prompt = (
                "Send the idea text - I'll classify it with AI."
                if lang == "en"
                else "Napisz treść pomysłu - sklasyfikuję ją AI."
            )
            await message.answer(prompt)
            return
        # text should be a category slug/name
        cats = categories_mod.all_categories(settings.vault_path)
        chosen = text.lower()
        if chosen in cats:
            _set_flow(message, step="await_idea", category=chosen)
            prompt = (
                f"Category: {chosen}. Now send the idea text."
                if lang == "en"
                else f"Kategoria: {chosen}. Teraz napisz treść pomysłu."
            )
            await message.answer(prompt)
        else:
            await message.answer("Unknown category, pick again.")
        return

    # --- Guided: awaiting idea text --------------------------------------
    if flow and flow.get("step") == "await_idea":
        category = flow.get("category")
        try:
            if category:
                result = capture_manual(
                    text, settings, category=str(category), subcategory="none"
                )
            else:
                result = capture(text, settings)
        except CaptureError as exc:
            await message.answer(f"Problem: {exc}")
            return
        _clear_flow(message)
        await message.answer(reply_text(result, lang), reply_markup=_menu(lang))
        return

    # --- Guided: awaiting new category -----------------------------------
    if flow and flow.get("step") == "await_category":
        parts = text.split(None, 1)
        name = parts[0]
        subs = parts[1].split(",") if len(parts) > 1 else []
        try:
            slug = categories_mod.add(settings.vault_path, name, subs)
        except ValueError as exc:
            await message.answer(f"Could not add: {exc}")
            return
        _clear_flow(message)
        done = "Added category" if lang == "en" else "Dodano kategorię"
        await message.answer(f"{done}: {slug}", reply_markup=_menu(lang))
        return

    # --- Free text: auto-route (AI if possible, else manual) -------------
    try:
        result = capture(text, settings)
    except CaptureError:
        try:
            result = capture_manual(text, settings)
        except CaptureError as exc:
            await message.answer(f"Problem: {exc}")
            return
    await message.answer(reply_text(result, lang), reply_markup=_menu(lang))


async def _main() -> None:
    import asyncio

    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot is idle (no polling).")
        while True:
            await asyncio.sleep(3600)
    bot = Bot(settings.telegram_bot_token, parse_mode=ParseMode.MARKDOWN)
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
