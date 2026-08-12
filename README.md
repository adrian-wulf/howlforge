# HowlForge 🐺

> Self-hosted **second brain for game production**. Capture an idea on your phone,
> let an AI classify it, and watch it land in an organized Markdown vault you own
> forever. Open-source, provider-agnostic, works at **$0** out of the box.

```
Telegram (capture)  →  AI classify (LiteLLM)  →  Markdown vault (source of truth)
                                            ↘   Obsidian / Dataview / CLI
```

## Why Markdown?

- **Zero vendor lock-in** - your notes are plain files that outlive any tool.
- **Git-native** - full history of every idea.
- **Obsidian / Logseq / Cursor / Claude Code read it today.**
- **AI-friendly** - LLMs love Markdown + YAML frontmatter.
- **Vector-ready** - add semantic search later (sqlite-vec / Qdrant).

## Features (current)

- **Provider-agnostic AI** via LiteLLM - Claude, Gemini, GPT, DeepSeek, **NVIDIA NIM**
  (free) and 100+ more. Default config runs on NVIDIA NIM = **$0**.
- **Controlled vocabulary** - statuses, priorities, categories/subcategories stay
  stable so your "tables" (Dataview) never break.
- **PL / EN support** - AI writes note content in your chosen language while keeping
  stable English keys for filtering.
- **Append-only safety** - AI synthesis never overwrites your source notes.
- **CLI** (`howlforge add`, `classify`, `init`, `doctor`) + Docker.

## Quick start

```bash
cp .env.example .env     # set NVIDIA_API_KEY (free) or any other provider key
pip install -e ".[dev]"
howlforge init           # bootstrap the vault layout
howlforge doctor         # check config + LLM model list
howlforge add "Idle farming where crops evolve into monsters at night"
```

Open the vault folder in Obsidian and filter notes with Dataview:

```dataview
TABLE status, priority, category
FROM "10 Projects"
WHERE status = "raw" AND project = "cowboy-farm"
```

## Roadmap

- [x] Vault schema + controlled vocabulary + PL/EN i18n
- [x] Classification prompt + LiteLLM integration + CLI
- [ ] Telegram bot (capture) + FastAPI
- [ ] Nightly AI synthesis into project pages / MOC (append-only)
- [ ] Lightweight web panel (list / filter / edit)
- [ ] Semantic search (sqlite-vec)
- [ ] JSON/CSV export for engine (Unity / Godot / Unreal)

## Architecture

```
Telegram Bot (aiogram)          ── (phase 2)
        │
        ▼
howlforge.ai  ── LiteLLM ──  NVIDIA NIM / Claude / Gemini / GPT / DeepSeek / …
   classify()                 (one API, automatic failover)
        │
        ▼
Vault  =  folder of .md files with YAML frontmatter
   Obsidian + Dataview  /  CLI  /  (web panel, phase 3)
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
