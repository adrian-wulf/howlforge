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

### Telegram bot (capture from your phone)

Set `TELEGRAM_BOT_TOKEN` (and optionally `TELEGRAM_CHAT_ID`) in `.env`, then:

```bash
howlforge-bot            # polling mode
```

Send any message to the bot; it classifies, saves to the vault and replies.

### HTTP API

```bash
uvicorn howlforge.server:app --host 0.0.0.0 --port 8000
curl -X POST localhost:8000/api/capture -H 'content-type: application/json' \
     -d '{"text": "co-op roguelike about a wolf pack"}'
# GET /health
```

### Web panel

A lightweight, self-hosted dashboard: **add ideas**, manage **projects**, and
list / filter / update notes. Works fully without an AI key.

```bash
uvicorn howlforge.server:app --host 0.0.0.0 --port 8000
# open http://localhost:8000/panel
```

- Add an idea (assign to a project, category, priority, status) - saved directly.
- Create projects and assign/reassign notes to them.
- JSON API: `GET /api/projects`, `POST /api/projects`,
  `GET /api/notes?project=&status=&category=`, `PATCH /api/notes/{path}`,
  `POST /api/capture` (`ai: false` = no key needed; `ai: true` = classify).

### Nightly synthesis (append-only)

Turn the last few days of ideas into an actionable digest. Each run writes a fresh
`generated: true` note under `_MOC/` - your hand-written notes are never touched.

```bash
howlforge synthesize                    # digest of last 7 days, all projects
howlforge synthesize --days 14          # longer window
howlforge synthesize --project cowboy-farm   # one project only
```

### Semantic search

Vector search over the vault using a lightweight SQLite index (no native extension).
Notes are embedded via the provider-agnostic `howl-embed` model.

```bash
howlforge index                         # embed all notes into .howlforge/embeddings.db
howlforge search "co-op wolf economy"   # rank notes by similarity
howlforge search "farming" -k 10        # more results
```

The index is stored under `<vault>/.howlforge/` and is excluded from Obsidian and
the note listing.

### Export to engine (JSON / CSV)

Load mechanics and assets into tooling or Unity / Godot / Unreal:

```bash
howlforge export --format json            # all notes as JSON (stdout)
howlforge export --format csv --out notes.csv
howlforge export --format json --project cowboy-farm --out cowboy.json
# GET /api/export?format=json&project=wolfpack
```

JSON includes tags/related as lists; CSV is flat scalar columns for spreadsheets.

Open the vault folder in Obsidian and filter notes with Dataview:

```dataview
TABLE status, priority, category
FROM "10 Projects"
WHERE status = "raw" AND project = "cowboy-farm"
```

## Roadmap

- [x] Vault schema + controlled vocabulary + PL/EN i18n
- [x] Classification prompt + LiteLLM integration + CLI
- [x] Telegram bot (capture) + FastAPI (HTTP capture endpoint)
- [x] Nightly AI synthesis into project pages / MOC (append-only)
- [x] Lightweight web panel (list / filter / edit)
- [x] Semantic search (sqlite-vec style)
- [x] JSON/CSV export for engine (Unity / Godot / Unreal)

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
