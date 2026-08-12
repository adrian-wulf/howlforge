"""Telegram bot: capture ideas from your phone.

Runs in polling mode (simplest for self-hosting). Every text message is routed
through :func:`howlforge.capture.capture`, then the user gets a confirmation.

Run with::

    howlforge-bot          # polling
    python -m howlforge.bot

Requires ``TELEGRAM_BOT_TOKEN`` and (optionally) ``TELEGRAM_CHAT_ID`` in ``.env``.
If ``TELEGRAM_CHAT_ID`` is set, only that chat is allowed to post.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .capture import CaptureError, capture, reply_text
from .config import get_settings

logger = logging.getLogger(__name__)

router = Router()


def _help_text(lang: str) -> str:
    if lang == "pl":
        return (
            "🐺 HowlForge\n"
            "Wyślij dowolną myśl/pomysł, a ja sklasyfikuję i zapiszę w vault.\n"
            "Polecenia:\n"
            "/help - ta pomoc\n"
            "/lang - pokaż język\n"
            "Przykład: \"idle farming z uprawami, które w nocy zamieniają się w potwory\""
        )
    return (
        "🐺 HowlForge\n"
        "Send any thought/idea and I'll classify it and save it to the vault.\n"
        "Commands:\n"
        "/help - this help\n"
        "/lang - show language\n"
        "Example: \"idle farming where crops evolve into monsters at night\""
    )


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(_help_text(get_settings().language), parse_mode=ParseMode.MARKDOWN)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(_help_text(get_settings().language), parse_mode=ParseMode.MARKDOWN)


@router.message(Command("lang"))
async def on_lang(message: Message) -> None:
    lang = get_settings().language
    await message.answer(f"Language: {lang}")


@router.message(Command("newcat"))
async def on_newcat(message: Message) -> None:
    """Add a new category: /newcat name sub1,sub2,..."""
    from . import categories as categories_mod

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
    lang = settings.language
    done = "Added category" if lang == "en" else "Dodano kategorię"
    await message.answer(f"{done}: {slug}")


@router.message(F.text)
async def on_text(message: Message) -> None:
    settings = get_settings()
    # Optional: restrict to one allowed chat.
    if settings.telegram_chat_id and str(message.chat.id) != settings.telegram_chat_id:
        return
    try:
        result = capture(message.text or "", settings)
    except CaptureError as exc:
        await message.answer(f"⚠️ {exc}")
        return
    await message.answer(reply_text(result, settings.language), parse_mode=ParseMode.MARKDOWN)


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Add it to .env and re-run."
        )
    bot = Bot(settings.telegram_bot_token, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("HowlForge bot starting in polling mode...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
