# HowlForge

> Self-hostowany **drugi mózg do produkcji gier**. Złap pomysł na telefonie, pozwól
> AI go sklasyfikować i zobacz, jak trafia do zorganizowanego Markdown vaulta, który
> jest w 100% Twój. Open-source, niezależny od providera, działa za **$0** od startu.

English | [Polski](README.pl.md)

```
Telegram (łapanie)  ->  AI klasyfikacja (LiteLLM)  ->  Markdown vault (źródło prawdy)
                                            \->  Obsidian / Dataview / panel web
```

## Dlaczego Markdown?

- **Zero vendor lock-in** - Twoje notatki to zwykłe pliki, które przetrwają każde narzędzie.
- **Git natywnie** - pełna historia każdego pomysłu.
- **Obsidian / Logseq / Cursor / Claude Code czytają to od razu.**
- **Przyjazne AI** - LLM-y kochają Markdown + YAML frontmatter.
- **Gotowe pod wektory** - wyszukiwanie semantyczne wbudowane.

## Funkcje

- **Niezależne od providera AI** przez LiteLLM - Claude, Gemini, GPT, DeepSeek,
  **NVIDIA NIM** (darmowe) i 100+ innych. Domyślny config działa na NVIDIA NIM = **$0**.
- **Kontrolowane słownictwo**, które możesz rozszerzać: statusy, priorytety oraz
  kategorie/podkategorie pozostają stabilne, więc tabele Dataview się nie psują.
- **PL / EN** interfejs, odpowiedzi bota i treść notatek AI - jeden ustawieniem.
- **Projekty** - twórz projekty i przypisuj do nich pomysły; notatki same się przenoszą.
- **Panel web** - dodawanie pomysłów, edycja notatek, filtry, dashboardy projektów.
  Działa **bez klucza AI**.
- **Bot Telegram** - łap pomysły z telefonu; dodawaj kategorie przez `/newcat`.
- **Nocna synteza AI** - digesty append-only; nigdy nie nadpisuje Twoich notatek.
- **Wyszukiwanie semantyczne** - indeks wektorowy w SQLite, bez natywnych rozszerzeń.
- **Eksport JSON/CSV** pod Unity / Godot / Unreal.
- **Autoryzacja** - opcjonalne hasło panelu/API do bezpiecznego hostingu.

## Architektura

```
Bot Telegram (aiogram)
        |
        v
classify()  -- LiteLLM -->  NVIDIA NIM / Claude / Gemini / GPT / DeepSeek / ...
        |
        v
Vault  =  folder plików .md z YAML frontmatter
   Panel web (FastAPI)  /  Obsidian + Dataview  /  CLI  /  Eksport
```

```
vault/
 00 Inbox/                surowe wpisy
 10 Projects/<slug>/      GDD, Mechanics, Art, Audio, Systems
 20 Systems/              uniwersalne mechaniki
 30 Assets & References/
 40 Inspiration/
 90 Archive/
 _MOC/                    Mapy treści + digesty syntezy AI
```

## Szybki start (lokalnie)

Wymagania: Python 3.11+, Git.

```bash
git clone https://github.com/adrian-wulf/howlforge.git
cd howlforge
cp .env.example .env        # opcjonalnie: HOWLFORGE_LANGUAGE, HOWLFORGE_PANEL_PASSWORD
pip install -e ".[dev]"
howlforge init              # utwórz strukturę vaulta
howlforge doctor            # sprawdź config + listę modeli LLM
howlforge run               # lub: uvicorn howlforge.server:app --port 8000
```

Potem otwórz **http://127.0.0.1:8000/panel**.

Możesz też użyć Makefile: `make dev`, `make run`, `make test`, `make lint`.

### Dodanie pomysłu (bez klucza AI)

```bash
curl -X POST localhost:8000/api/capture -H 'content-type: application/json' \
     -d '{"text":"Kooperacyjny roguelike o wilczej sfory","ai":false,"project":"wolfpack","category":"gameplay"}'
```

Albo po prostu użyj formularza "Dodaj pomysł" w panelu.

### Klasyfikacja AI (opcjonalna, wymaga klucza)

Ustaw jeden klucz w `.env` (NVIDIA NIM jest darmowy):

```bash
NVIDIA_API_KEY=...          # darmowy domyślny
# lub ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY
```

```bash
howlforge add "Idle farming, w którym uprawy w nocy zamieniają się w potwory"
```

### Bot Telegram

Ustaw `TELEGRAM_BOT_TOKEN` w `.env`, potem:

```bash
howlforge-bot               # lub: python -m howlforge.bot
```

**Ogranicz tylko do siebie (opcjonalnie):** ustaw jeden lub kilka ID czatu/użytkownika -
bot ignoruje wszystkich innych.

```bash
TELEGRAM_CHAT_IDS=123456789,987654321
```

Komendy: `/help`, `/lang`, `/newcat Nazwa pod1,pod2`, `/cancel`.

Bot pokazuje klawiaturę: **Dodaj pomysł** (wybierz kategorię, potem napisz notatkę),
**Nowa kategoria**, **Pomoc**, **Język**. Albo po prostu napisz wiadomość - bot sam
zdecyduje, co z nią zrobić.

### Panel web + API

`uvicorn howlforge.server:app --port 8000`, potem:

- Panel: `http://localhost:8000/panel`
- Dodawanie pomysłu / projektu / kategorii, edycja notatek, dashboardy z panelu.
- API: `GET /api/notes`, `GET /api/notes/{path}`, `PATCH /api/notes/{path}`,
  `POST /api/capture`, `GET /api/projects`, `POST /api/projects`,
  `GET /api/categories`, `POST /api/categories`, `GET /api/search`, `GET /api/export`.

### Zabezpieczenie panelu

```bash
HOWLFORGE_PANEL_PASSWORD=TwojeMocneHaslo!
```

Puste = otwarty panel (tylko lokalnie). Ustawione = wymagane logowanie (strony
przekierowują, API zwraca `401`).

### Język

```bash
HOWLFORGE_LANGUAGE=pl       # lub en
```

Steruje panelem web, odpowiedziami bota i treścią notatek pisanych przez AI.

## Deploy na małym VPS (darmowo / tanio)

Vault trzyma dane na dysku, więc potrzebujesz hosta z **trwałym systemem plików** i
procesem **działającym cały czas**. Dobre opcje:

| Host | Koszt | Uwagi |
|---|---|---|
| **Oracle Cloud ARM** (free tier) | $0 | 4 vCPU / 24 GB, zawsze włączony, stały dysk. Najlepsze dla bota 24/7. |
| **Hetzner Cloud** (CX22) | ~EUR 3,79/mies. | Tanio, niezawodnie, łatwa rejestracja kartą. |
| **Vultr / RackNerd / Scaleway / IONOS** | $2,50-5/mies. | Wystarczy na małe potrzeby. |

Czysty serverless (Netlify / Vercel) **nie** pasuje: efemeryczny dysk + brak długo
działającego procesu dla bota polling.

### Instalacja jednym skryptem (Oracle, Hetzner, dowolny VPS na Ubuntu)

Na serwerze:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/adrian-wulf/howlforge/main/deploy/oracle/setup.sh)
```

Skrypt instaluje Docker, klonuje repo, prosi o uzupełnienie `.env` i uruchamia
`api` + `bot` przez `deploy/oracle/docker-compose.prod.yml`. Vault jest w nazwanym
wolumenie Docker.

Potem otwórz `http://<ip-serwera>:8000` (najpierw ustaw `HOWLFORGE_PANEL_PASSWORD`).

### Opcjonalne HTTPS przez Caddy (wymaga domeny)

```bash
HOWLFORGE_DOMAIN=howl.example.com docker compose --profile https \
  -f deploy/oracle/docker-compose.prod.yml up -d
```

## Rozwój

```bash
pip install -e ".[dev]"
pytest                    # 79+ testów
ruff check .              # lint
```

### Struktura projektu

```
howlforge/
  vocabulary.py     kontrolowane słownictwo (statusy, priorytety, kategorie)
  categories.py     rozszerzalne kategorie per-vault
  schema.py         model notatki + YAML frontmatter
  i18n.py           etykiety PL/EN + teksty UI
  llm.py            klient LiteLLM (kompletacje + embeddingi)
  classify.py       pipeline klasyfikacji (prompt -> JSON -> walidacja)
  capture.py        usługa łapania pomysłów (manualna + AI)
  synthesize.py     nocne digesty append-only
  search.py         wyszukiwanie semantyczne (wektory w SQLite)
  export.py         eksport JSON/CSV
  vault.py          operacje na folderze vaulta
  server.py         aplikacja FastAPI (panel + API)
  bot.py            bot Telegram (aiogram)
  cli.py            CLI howlforge
  prompts/          szablony promptów EN/PL
  templates/        HTML panelu web
deploy/oracle/      deploy na VPS (setup.sh + compose produkcyjny)
```

## Roadmap

- [x] Schemat vaulta + kontrolowane słownictwo + i18n PL/EN
- [x] Prompt klasyfikacji + integracja LiteLLM + CLI
- [x] Bot Telegram + FastAPI
- [x] Nocna synteza AI (append-only)
- [x] Panel web (dodawanie/edycja/filtry, projekty, dashboardy)
- [x] Wyszukiwanie semantyczne
- [x] Eksport JSON/CSV
- [x] Autoryzacja panelu + deploy na VPS

## Licencja

MIT
