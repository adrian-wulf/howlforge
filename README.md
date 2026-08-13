# HowlForge

> Self-hosted **second brain** for everything you think, capture and plan. Catch a
> thought on your phone, let an AI file it, and watch it land in an organized
> Markdown vault you own forever. Game production, research, writing, personal
> notes, side projects - one inbox, one system. Open-source, provider-agnostic,
> works at **$0** out of the box.

[Polski](README.pl.md) | English

```
Telegram / Web / CLI  ->  AI classify (LiteLLM)  ->  Markdown vault (source of truth)
                                             \->  Obsidian / Dataview / Web panel
```

## What is HowlForge?

A self-hosted personal knowledge base (PKM / second brain). You capture, it organizes:

- **Capture from anywhere** - Telegram on your phone, the web panel, the CLI, or a
  plain HTTP API.
- **AI does the triage** - note type, category, tags, project, status, priority,
  title and summary. Optional: everything works without an AI key.
- **Everything lands in plain Markdown files** with YAML frontmatter, in a folder
  tree you control.
- **You read and edit with anything** - the built-in panel, Obsidian, Logseq,
  VS Code, git, any agent.

HowlForge was born as a game-production tool (that's why the built-in vocabulary
knows GDD, mechanics, art, audio...), but the vocabulary is fully extensible -
categories, statuses and priorities - so the same engine drives any domain:
research, writing, studying, startups, personal life.

### Example workflows

| Domain | What you get |
|---|---|
| **Game production** | GDD pages, mechanics, art briefs, marketing ideas; per-project Kanban boards |
| **Personal second brain** | phone captures -> auto-filed inbox, nightly AI digests, semantic search |
| **Research & writing** | sources in `30 Assets & References`, influences in `40 Inspiration`, synthesis digests |
| **Any project** | one folder per project, statuses/priorities, Kanban, JSON/CSV export for tooling |

## Why Markdown?

- **Zero vendor lock-in** - your notes are plain files that outlive any tool.
- **Git-native** - full history of every note.
- **Obsidian / Logseq / Cursor / Claude Code read it today.**
- **AI-friendly** - LLMs love Markdown + YAML frontmatter.
- **Semantic search built in** - SQLite vectors, no native extension needed.

## Features

- **Provider-agnostic AI** via LiteLLM - Claude, Gemini, GPT, DeepSeek, **NVIDIA NIM**
  (free) and 100+ more. Default config runs on NVIDIA NIM = **$0**.
- **AI is optional** - capture, panel, Kanban and search all work without any key.
- **Controlled vocabulary** that you extend: statuses, priorities and
  categories/subcategories stay validated so your Dataview tables never break.
  The built-in set is game-dev flavored; add your own for any domain.
- **PL / EN** UI, bot replies and AI note content, controlled by one setting.
- **Projects** - create projects and assign notes to them; notes move folders. Each
  project has a **Kanban board** (category columns, status/priority color + symbol
  badges, filters).
- **Web panel** - add/edit/**delete** notes, filter, projects, per-project
  dashboards. Works **without any AI key**.
- **Telegram bot** - capture ideas from your phone; add categories via `/newcat`;
  add and delete notes, projects and categories via the reply keyboard.
- **Nightly AI synthesis** - append-only digests; never overwrites your notes.
- **Semantic search** - SQLite vector index, no native extension needed.
- **JSON/CSV export** - for spreadsheets, scripts, game engines, any tooling.
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
 00 Inbox/                raw captures waiting for triage
 10 Projects/<slug>/      one folder per project (subfolders follow note types)
 20 Systems/              reusable systems and patterns
 30 Assets & References/  reusable assets, sources, research links
 40 Inspiration/          mood, influences, inspiration
 90 Archive/              done / rejected / dormant
 _MOC/                    Maps of Content + AI synthesis digests
```

The layout is a convention, not a cage: rename folders, add your own categories and
subcategories, and notes follow their frontmatter.

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

### Add a note (no AI key needed)

```bash
curl -X POST localhost:8000/api/capture -H 'content-type: application/json' \
     -d '{"text":"Weekly review template for the whole team","ai":false,"project":"work","category":"production","subcategory":"tasks"}'
```

Or just use the "Add an idea" form in the panel.

### AI classification (optional, needs a key)

Set one key in `.env` (NVIDIA NIM is free):

```bash
NVIDIA_API_KEY=...          # free default
# or ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY
```

```bash
howlforge add "A newsletter issue about the cost of context switching"
howlforge add "Co-op roguelike about a wolf pack"
```

Classification works in any domain. Add your own categories from the panel or bot
and the classifier will use them.

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

Commands: `/help`, `/lang`, `/newcat Name sub1,sub2`, `/status`, `/cancel`.

The reply keyboard has seven buttons:

| Button | What it does |
|---|---|
| **Add idea** | Guided capture: pick project -> pick category -> type the note |
| **New project** | Create a project folder |
| **New category** | Add a note category (with subcategories) |
| **Project** | Set a **default project** - every idea then goes to it automatically |
| **Language** | Toggle PL/EN |
| **Delete** | Delete a note, project or category |
| **Help** | Show help |

The chosen **language** and **default project** are saved per user in
`<vault>/.howlforge/bot_state.json`, so they survive bot restarts. Just type a
message and the bot auto-routes it (AI classify, or manual if no key), assigning
it to your default project when one is set.

### Web panel + API

`uvicorn howlforge.server:app --port 8000`, then:

- Panel: `http://localhost:8000/panel`
- Add note / project / category / edit notes / dashboards from the panel.
- **Delete** notes, projects and categories from the panel.
- API: `GET /api/notes`, `GET /api/notes/{path}`, `PATCH /api/notes/{path}`,
  `DELETE /api/notes/{path}`, `POST /api/capture`, `GET /api/projects`,
  `POST /api/projects`, `DELETE /api/projects/{slug}`, `GET /api/categories`,
  `POST /api/categories`, `DELETE /api/categories/{name}`, `GET /api/search`,
  `GET /api/export`.

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

### Custom vocabulary (categories, statuses, priorities)

Everything is customizable from the panel (or by editing files in the vault):

- **Categories** - add/remove your own categories + subcategories
  (`<vault>/.howlforge/categories.json`). Each category can carry a short
  **description** that the classifier reads when choosing where a note belongs
  (panel form, or bot: `Name subs | description`). The built-in set is game-dev
  flavored; add e.g. `books`, `health`, `finance`, `travel` and the classifier,
  filters and Kanban pick them up.
- **Statuses** and **priorities** - add/remove with your own Polish + English labels
  and colors (`<vault>/.howlforge/vocab.json`). They appear in the Kanban board,
  filters and classification.
- **Note types** (`idea`, `note`, `system`, ...) are defined in
  `howlforge/vocabulary.py` - edit there if you want a different set.
- Built-in values can't be removed, but you can add as many as you like.

The Kanban board is at `/panel/project/<slug>/board` (or click the project, then
"Board"). Columns are **categories**; each card shows a **status** and **priority**
badge (color + symbol). Drag cards between category columns to re-categorize, and
filter by status and priority. Use the left/right arrows on a column header to
reorder columns (saved per project).

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
pytest                    # test suite
ruff check .              # lint
```

### Project layout

```
howlforge/
  vocabulary.py     controlled vocabulary (note types, statuses, priorities, categories)
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

## Troubleshooting

**Vault permissions.** If you run via Docker (`make up`) and later can't write notes
locally, the `vault/` folder was likely created by Docker as `root`. Fix it once:

```bash
sudo chown -R "$USER":"$USER" vault
howlforge init
```

The `Makefile` `up` target and `deploy/oracle/setup.sh` already create `vault/`
for your user to prevent this.

## License

MIT
