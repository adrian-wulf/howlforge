# HowlForge

> Self-hosted **second brain for game production**. Capture an idea on your phone,
> let an AI classify it, and watch it land in an organized Markdown vault you own
> forever. Open-source, provider-agnostic, works at **$0** out of the box.

[Polski](README.pl.md) | English

```
Telegram (capture)  ->  AI classify (LiteLLM)  ->  Markdown vault (source of truth)
                                        \->  Obsidian / Dataview / Web panel
```

## Why Markdown?

- **Zero vendor lock-in** - your notes are plain files that outlive any tool.
- **Git-native** - full history of every idea.
- **Obsidian / Logseq / Cursor / Claude Code read it today.**
- **AI-friendly** - LLMs love Markdown + YAML frontmatter.
- **Vector-ready** - add semantic search easily (built in).

## Features

- **Provider-agnostic AI** via LiteLLM - Claude, Gemini, GPT, DeepSeek, **NVIDIA NIM**
  (free) and 100+ more. Default config runs on NVIDIA NIM = **$0**.
- **Controlled vocabulary** that you can extend: statuses, priorities and
  categories/subcategories stay stable so your Dataview tables never break.
- **PL / EN** UI, bot replies and AI note content, controlled by one setting.
- **Projects** - create projects and assign ideas to them; notes move folders.
- **Web panel** - add ideas, edit notes, filter, per-project dashboards. Works
  **without any AI key**.
- **Telegram bot** - capture ideas from your phone; add categories via `/newcat`.
- **Nightly AI synthesis** - append-only digests; never overwrites your notes.
- **Semantic search** - SQLite vector index, no native extension needed.
- **JSON/CSV export** for Unity / Godot / Unreal.
- **Auth** - optional panel/API password for safe hosting.

## Architecture

```
Telegram Bot (aiogram)
        |
        v
classify()  -- LiteLLM -->  NVIDIA NIM / Claude / Gemini / GPT / DeepSeek / ...
        |
        v
Vault  =  folder of .md files with YAML frontmatter
   Web panel (FastAPI)  /  Obsidian + Dataview  /  CLI  /  Export
```

```
vault/
 00 Inbox/                raw captures
 10 Projects/<slug>/      GDD, Mechanics, Art, Audio, Systems
 20 Systems/              universal mechanics
 30 Assets & References/
 40 Inspiration/
 90 Archive/
 _MOC/                    Maps of Content + AI synthesis digests
```

## Quick start (local)

Requirements: Python 3.11+, Git.

```bash
git clone https://github.com/adrian-wulf/howlforge.git
cd howlforge
cp .env.example .env        # optional: HOWLFORGE_LANGUAGE, HOWLFORGE_PANEL_PASSWORD
pip install -e ".[dev]"
howlforge init              # create the vault layout
howlforge doctor            # check config + LLM model list
uvicorn howlforge.server:app --port 8000   # or: make run
```

Then open **http://127.0.0.1:8000/panel**.

Or use the Makefile: `make dev`, `make run`, `make test`, `make lint`.

### Add an idea (no AI key needed)

```bash
curl -X POST localhost:8000/api/capture -H 'content-type: application/json' \
     -d '{"text":"Co-op wolf pack roguelike","ai":false,"project":"wolfpack","category":"gameplay"}'
```

Or just use the "Add an idea" form in the panel.

### AI classification (optional, needs a key)

Set one key in `.env` (NVIDIA NIM is free):

```bash
NVIDIA_API_KEY=...          # free default
# or ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY
```

```bash
howlforge add "Idle farming where crops evolve into monsters at night"
```

### Telegram bot

Set `TELEGRAM_BOT_TOKEN` in `.env`, then:

```bash
howlforge-bot               # or: python -m howlforge.bot
```

**Restrict to you only (optional):** set one or several chat/user IDs - the bot
ignores everyone else.

```bash
TELEGRAM_CHAT_IDS=123456789,987654321
```

Commands: `/help`, `/lang`, `/newcat Name sub1,sub2`, `/cancel`.

The bot shows a reply keyboard: **Add idea** (pick a category, then type the note),
**New category**, **Help**, **Language**. Or just type a message and it auto-routes.

### Web panel + API

`uvicorn howlforge.server:app --port 8000`, then:

- Panel: `http://localhost:8000/panel`
- Add idea / project / category / edit notes / dashboards from the panel.
- API: `GET /api/notes`, `GET /api/notes/{path}`, `PATCH /api/notes/{path}`,
  `POST /api/capture`, `GET /api/projects`, `POST /api/projects`,
  `GET /api/categories`, `POST /api/categories`, `GET /api/search`, `GET /api/export`.

### Protect the panel

```bash
HOWLFORGE_PANEL_PASSWORD=YourStrongPassword!
```

Empty = open panel (local only). Set = login required (pages redirect, API `401`).

### Language

```bash
HOWLFORGE_LANGUAGE=pl       # or en
```

Controls the web panel, bot replies and AI-written note content.

## Deploy on a small VPS (free / cheap)

The vault lives on disk, so use a host with a **persistent filesystem** and an
**always-on** process. Good options:

| Host | Cost | Notes |
|---|---|---|
| **Oracle Cloud ARM** (free tier) | $0 | 4 vCPU / 24 GB, always-on, persistent disk. Best for the bot 24/7. |
| **Hetzner Cloud** (CX22) | ~EUR 3.79/mo | Cheap, reliable, easy card signup. |
| **Vultr / RackNerd / Scaleway / IONOS** | $2.50-5/mo | Fine for small needs. |

Pure serverless (Netlify / Vercel) is **not** suitable: ephemeral filesystem + no
long-running process for the polling bot.

### One-shot install (Oracle, Hetzner, any Ubuntu VPS)

On your server:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/adrian-wulf/howlforge/main/deploy/oracle/setup.sh)
```

It installs Docker, clones the repo, prompts you to fill `.env`, and starts
`api` + `bot` via `deploy/oracle/docker-compose.prod.yml`. The vault is stored in a
named Docker volume.

Then open `http://<server-ip>:8000` (set `HOWLFORGE_PANEL_PASSWORD` first).

### Optional HTTPS with Caddy (needs a domain)

```bash
HOWLFORGE_DOMAIN=howl.example.com docker compose --profile https \
  -f deploy/oracle/docker-compose.prod.yml up -d
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # 87 tests
ruff check .              # lint
```

### Project layout

```
howlforge/
  vocabulary.py     controlled vocabulary (statuses, priorities, categories)
  categories.py     extendable per-vault categories
  schema.py         note model + YAML frontmatter
  i18n.py           PL/EN labels + UI strings
  llm.py            LiteLLM client (completions + embeddings)
  classify.py       classification pipeline (prompt -> JSON -> validate)
  capture.py        capture service (manual + AI)
  synthesize.py     nightly append-only digests
  search.py         semantic search (SQLite vectors)
  export.py         JSON/CSV export
  vault.py          vault folder operations
  server.py         FastAPI app (panel + API)
  bot.py            Telegram bot (aiogram)
  cli.py            howlforge CLI
  prompts/          EN/PL prompt templates
  templates/        web panel HTML
deploy/oracle/      VPS deploy (setup.sh + production compose)
```

## Roadmap

- [x] Vault schema + controlled vocabulary + PL/EN i18n
- [x] Classification prompt + LiteLLM integration + CLI
- [x] Telegram bot + FastAPI
- [x] Nightly AI synthesis (append-only)
- [x] Web panel (add/edit/filter, projects, dashboards)
- [x] Semantic search
- [x] JSON/CSV export
- [x] Panel auth + VPS deploy

## License

MIT
