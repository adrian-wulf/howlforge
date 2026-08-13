# HowlForge

> Self-hostowany **drugi mózg** na wszystko, co myślisz, łapiesz i planujesz. Złap
> myśl na telefonie, pozwól AI ją posegregować i zobacz, jak trafia do
> zorganizowanego Markdown vaulta, który jest w 100% Twój. Produkcja gier, research,
> pisanie, notatki osobiste, projekty poboczne - jedna skrzynka, jeden system.
> Open-source, niezależny od providera, działa za **$0** od startu.

[English](README.md) | Polski

```
Telegram / Web / CLI  ->  AI klasyfikacja (LiteLLM)  ->  Markdown vault (źródło prawdy)
                                                 \->  Obsidian / Dataview / panel web
```

## Czym jest HowlForge?

Self-hostowana baza wiedzy osobistej (PKM / drugi mózg). Ty łapiesz, ono organizuje:

- **Łapanie zewsząd** - Telegram na telefonie, panel web, CLI albo zwykłe HTTP API.
- **AI robi segregację** - typ notatki, kategoria, tagi, projekt, status, priorytet,
  tytuł i podsumowanie. Opcjonalnie: wszystko działa bez klucza AI.
- **Wszystko ląduje w zwykłych plikach Markdown** z YAML frontmatter, w strukturze
  folderów, którą kontrolujesz.
- **Czytasz i edytujesz czym chcesz** - wbudowanym panelem, Obsidianem, Logseq,
  VS Code, gitem, dowolnym agentem.

HowlForge narodził się jako narzędzie do produkcji gier (dlatego wbudowane
słownictwo zna GDD, mechaniki, art, audio...), ale słownictwo jest w pełni
rozszerzalne - kategorie, statusy i priorytety - więc ten sam silnik obsłuży każdą
dziedzinę: research, pisanie, naukę, startupy, życie osobiste.

### Przykładowe zastosowania

| Dziedzina | Co dostajesz |
|---|---|
| **Produkcja gier** | strony GDD, mechaniki, briefy art, pomysły marketingowe; tablice Kanban per projekt |
| **Osobisty drugi mózg** | zapis z telefonu -> automatycznie posegregowany inbox, nocne digesty AI, wyszukiwanie semantyczne |
| **Research i pisanie** | źródła w `30 Assets & References`, inspiracje w `40 Inspiration`, digesty syntezy |
| **Dowolny projekt** | folder na projekt, statusy/priorytety, Kanban, eksport JSON/CSV do narzędzi |

## Dlaczego Markdown?

- **Zero vendor lock-in** - Twoje notatki to zwykłe pliki, które przetrwają każde narzędzie.
- **Git natywnie** - pełna historia każdej notatki.
- **Obsidian / Logseq / Cursor / Claude Code czytają to od razu.**
- **Przyjazne AI** - LLM-y kochają Markdown + YAML frontmatter.
- **Wyszukiwanie semantyczne wbudowane** - wektory w SQLite, bez natywnych rozszerzeń.

## Funkcje

- **Niezależne od providera AI** przez LiteLLM - Claude, Gemini, GPT, DeepSeek,
  **NVIDIA NIM** (darmowe) i 100+ innych. Domyślny config działa na NVIDIA NIM = **$0**.
- **AI jest opcjonalne** - łapanie, panel, Kanban i wyszukiwanie działają bez klucza.
- **Kontrolowane słownictwo**, które rozszerzasz: statusy, priorytety oraz
  kategorie/podkategorie pozostają walidowane, więc tabele Dataview się nie psują.
  Wbudowany zestaw jest pod game dev; dodaj własne pod dowolną dziedzinę.
- **PL / EN** interfejs, odpowiedzi bota i treść notatek AI - jednym ustawieniem.
- **Projekty** - twórz projekty i przypisuj do nich notatki; notatki same się
  przenoszą. Każdy projekt ma **tablicę Kanban** (kolumny kategorii, badge
  statusu/priorytetu z kolorem i symbolem, filtry).
- **Panel web** - dodawanie/edycja/**usuwanie** notatek, filtry, projekty,
  dashboardy. Działa **bez klucza AI**.
- **Bot Telegram** - łap pomysły z telefonu; dodawaj kategorie przez `/newcat`;
  dodawaj i usuwaj notatki, projekty i kategorie przez klawiaturę.
- **Nocna synteza AI** - digesty append-only; nigdy nie nadpisuje Twoich notatek.
- **Wyszukiwanie semantyczne** - indeks wektorowy w SQLite, bez natywnych rozszerzeń.
- **Eksport JSON/CSV** - do arkuszy, skryptów, silników gier, dowolnych narzędzi.
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
 00 Inbox/                surowe wpisy czekające na segregację
 10 Projects/<slug>/      folder na projekt (podfoldery według typów notatek)
 20 Systems/              systemy i wzorce wielokrotnego użytku
 30 Assets & References/  assety, źródła, linki badawcze
 40 Inspiration/          nastrój, wpływy, inspiracje
 90 Archive/              zrobione / odrzucone / uśpione
 _MOC/                    Mapy treści + digesty syntezy AI
```

Układ to konwencja, nie klatka: zmieniaj nazwy folderów, dodawaj własne kategorie
i podkategorie, a notatki podążają za swoim frontmatterem.

## Szybki start (lokalnie)

Wymagania: Python 3.11+, Git.

```bash
git clone https://github.com/adrian-wulf/howlforge.git
cd howlforge
cp .env.example .env        # opcjonalnie: HOWLFORGE_LANGUAGE, HOWLFORGE_PANEL_PASSWORD
pip install -e ".[dev]"
howlforge init              # utwórz strukturę vaulta
howlforge doctor            # sprawdź config + listę modeli LLM
uvicorn howlforge.server:app --port 8000   # lub: make run
```

Potem otwórz **http://127.0.0.1:8000/panel**.

Możesz też użyć Makefile: `make dev`, `make run`, `make test`, `make lint`.

### Dodanie notatki (bez klucza AI)

```bash
curl -X POST localhost:8000/api/capture -H 'content-type: application/json' \
     -d '{"text":"Szablon cotygodniowego przeglądu dla całego zespołu","ai":false,"project":"praca","category":"production","subcategory":"tasks"}'
```

Albo po prostu użyj formularza "Dodaj pomysł" w panelu.

### Klasyfikacja AI (opcjonalna, wymaga klucza)

Ustaw jeden klucz w `.env` (NVIDIA NIM jest darmowy):

```bash
NVIDIA_API_KEY=...          # darmowy domyślny
# lub ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY
```

```bash
howlforge add "Numer newslettera o koszcie przełączania kontekstu"
howlforge add "Kooperacyjny roguelike o wilczej sforze"
```

Klasyfikacja działa w każdej dziedzinie. Dodaj własne kategorie z panelu lub bota,
a klasyfikator zacznie ich używać.

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

Komendy: `/help`, `/lang`, `/newcat Nazwa pod1,pod2`, `/status`, `/cancel`.

Klawiatura ma siedem przycisków:

| Przycisk | Co robi |
|---|---|
| **Dodaj pomysł** | Prowadzony zapis: wybierz projekt -> wybierz kategorię -> napisz notatkę |
| **Nowy projekt** | Tworzy folder projektu |
| **Nowa kategoria** | Dodaje kategorię notatek (z podkategoriami) |
| **Projekt** | Ustawia **domyślny projekt** - każdy pomysł trafia do niego automatycznie |
| **Język** | Przełącza PL/EN |
| **Usuń** | Usuwa notatkę, projekt lub kategorię |
| **Pomoc** | Pokazuje pomoc |

Wybrany **język** i **domyślny projekt** są zapisywane per użytkownik w
`<vault>/.howlforge/bot_state.json`, więc przetrwają restart bota. Po prostu napisz
wiadomość, a bot sam ją obsłuży (klasyfikacja AI lub ręcznie, gdy brak klucza),
przypisując ją do domyślnego projektu, jeśli jest ustawiony.

### Panel web + API

`uvicorn howlforge.server:app --port 8000`, potem:

- Panel: `http://localhost:8000/panel`
- Dodawanie notatki / projektu / kategorii, edycja notatek, dashboardy z panelu.
- **Usuwanie** notatek, projektów i kategorii z panelu.
- API: `GET /api/notes`, `GET /api/notes/{path}`, `PATCH /api/notes/{path}`,
  `DELETE /api/notes/{path}`, `POST /api/capture`, `GET /api/projects`,
  `POST /api/projects`, `DELETE /api/projects/{slug}`, `GET /api/categories`,
  `POST /api/categories`, `DELETE /api/categories/{name}`, `GET /api/search`,
  `GET /api/export`.

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

### Własne słownictwo (kategorie, statusy, priorytety)

Wszystko można dostosować z panelu (albo edytując pliki w vaulcie):

- **Kategorie** - dodawaj/usuwaj własne kategorie i podkategorie
  (`<vault>/.howlforge/categories.json`). Wbudowany zestaw jest pod game dev;
  dodaj np. `ksiazki`, `zdrowie`, `finanse`, `podroze`, a klasyfikator, filtry
  i Kanban od razu je podchwycą.
- **Statusy** i **priorytety** - dodawaj/usuwaj z własnymi polskimi i angielskimi
  etykietami oraz kolorami (`<vault>/.howlforge/vocab.json`). Pojawiają się na
  tablicy Kanban, w filtrach i klasyfikacji.
- **Typy notatek** (`idea`, `note`, `system`, ...) są zdefiniowane w
  `howlforge/vocabulary.py` - edytuj tam, jeśli chcesz inny zestaw.
- Wartości wbudowanych nie można usunąć, ale możesz dodać ile chcesz.

Tablica Kanban jest pod `/panel/project/<slug>/board` (albo wejdź w projekt i kliknij
"Tablica"). Kolumny to **kategorie**; każda karta ma badge **statusu** i **priorytetu**
(kolor + symbol). Przeciągaj karty między kolumnami kategorii, aby zmienić kategorię,
i filtruj po statusie oraz priorytecie. Strzałki lewo/prawo w nagłówku kolumny
zmieniają kolejność kolumn (zapamiętywana per projekt).

## Deploy na małym VPS (darmowo / tanio)

Vault trzyma dane na dysku, więc potrzebujesz hosta z **trwałym systemem plików** i
procesem **działającym cały czas**. Dobre opcje:

| Host | Koszt | Uwagi |
|---|---|---|
| **Oracle Cloud ARM** (free tier) | $0 | 4 vCPU / 24 GB, zawsze włączony, stały dysk. Najlepsze dla bota 24/7. |
| **Hetzner Cloud** (CX22) | ~EUR 3,79/mies. | Tanio, niezawodnie, łatwa rejestracja kartą. |
| **Vultr / RackNerd / Scaleway / IONOS** | $2,50-5/mies. | Wystarczy na małe potrzeby. |

Czysty serverless (Netlify / Vercel) **nie** pasuje: tymczasowy dysk + brak długo
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
pytest                    # testy
ruff check .              # lint
```

### Struktura projektu

```
howlforge/
  vocabulary.py     kontrolowane słownictwo (typy notatek, statusy, priorytety, kategorie)
  categories.py     rozszerzalne kategorie per-vault
  schema.py         model notatki + YAML frontmatter
  i18n.py           etykiety PL/EN + teksty UI
  llm.py            klient LiteLLM (kompletacje + embeddingi)
  classify.py       pipeline klasyfikacji (prompt -> JSON -> walidacja)
  capture.py        usługa łapania (manualna + AI)
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

## Rozwiązywanie problemów

**Uprawnienia vaulta.** Jeśli uruchamiasz przez Docker (`make up`) i potem nie możesz
zapisywać notatek lokalnie, folder `vault/` został prawdopodobnie utworzony przez
Docker jako `root`. Napraw raz:

```bash
sudo chown -R "$USER":"$USER" vault
howlforge init
```

Cel `up` w Makefile oraz `deploy/oracle/setup.sh` już tworzą `vault/` dla Twojego
użytkownika, żeby temu zapobiec.

## Licencja

MIT
