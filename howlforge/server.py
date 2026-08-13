"""FastAPI app: health check + an HTTP capture endpoint.

The HTTP endpoint lets you test the capture pipeline without Telegram
(``curl -X POST localhost:8000/api/capture -d '{"text": "..."}``). It shares the
same :func:`howlforge.capture.capture` service as the Telegram bot.

Run with::

    uvicorn howlforge.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, RedirectResponse

from . import board_order
from . import categories as categories_mod
from . import vocab as vocab_mod
from .capture import CaptureError, capture, capture_manual
from .config import get_settings
from .i18n import ui_strings
from .schema import Note
from .vault import (
    create_project,
    delete_note,
    delete_project,
    list_notes,
    list_projects,
    read_note,
    update_note,
)

app = FastAPI(title="HowlForge", version="0.1.0")
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_COOKIE = "howlforge_auth"
_PUBLIC_PATHS = {"/login", "/health", "/logout", "/favicon.ico"}


def _auth_token(password: str) -> str:
    return hmac.new(password.encode(), b"howlforge-panel", hashlib.sha256).hexdigest()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    settings = get_settings()
    password = settings.panel_password
    if not password:
        return await call_next(request)
    path = request.url.path
    if path in _PUBLIC_PATHS or path.startswith("/login") or path.startswith("/logout"):
        return await call_next(request)
    if request.cookies.get(_COOKIE) == _auth_token(password):
        return await call_next(request)
    if path.startswith("/api"):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login")
def login_page(request: Request) -> Response:
    ui = ui_strings(get_settings().language)
    return _templates.TemplateResponse(request, "login.html", {"request": request, "ui": ui})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    password = form.get("password") or ""
    settings = get_settings()
    if hmac.compare_digest(password, settings.panel_password):
        resp = RedirectResponse(url="/panel", status_code=303)
        resp.set_cookie(
            _COOKIE, _auth_token(settings.panel_password), httponly=True, samesite="lax"
        )
        return resp
    ui = ui_strings(settings.language)
    return _templates.TemplateResponse(
        request, "login.html", {"request": request, "ui": ui, "error": ui["bad_password"]}
    )


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(_COOKIE)
    return resp


class CaptureRequest(BaseModel):
    text: str = Field(..., min_length=1)
    ai: bool = False
    project: Optional[str] = None
    category: str = "misc"
    subcategory: str = "none"
    status: str = "raw"
    priority: str = "backlog"
    tags: List[str] = Field(default_factory=list)


class CaptureResponse(BaseModel):
    ok: bool
    path: str
    title: str
    type: str
    category: str
    subcategory: str


class UpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    project: Optional[str] = None
    body: Optional[str] = None


def _summarize(note: Note, vault_root: Path, path: Path) -> Dict[str, object]:
    return {
        "path": str(path.relative_to(vault_root)),
        "title": note.title,
        "type": note.type,
        "status": note.status,
        "priority": note.priority,
        "category": note.category,
        "subcategory": note.subcategory,
        "project": note.project or "",
        "tags": note.tags,
        "generated": note.generated,
        "created": note.created,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/panel")
def panel(request: Request) -> Response:
    settings = get_settings()
    rows = [
        _summarize(
            Note.from_markdown(p.read_text(encoding="utf-8")), settings.vault_path, p
        )
        for p in list_notes(settings.vault_path)
    ]
    from . import vocabulary

    projects = list_projects(settings.vault_path)
    ui = ui_strings(settings.language)
    custom_categories = categories_mod.load(settings.vault_path)
    custom_vocab = vocab_mod.load(settings.vault_path)
    return _templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "ui": ui,
            "auth_enabled": bool(settings.panel_password),
            "notes": rows,
            "projects": projects,
            "custom_categories": custom_categories,
            "custom_descriptions": categories_mod.load_descriptions(settings.vault_path),
            "custom_statuses": custom_vocab.get("statuses", []),
            "custom_priorities": custom_vocab.get("priorities", []),
            "statuses": vocabulary.STATUSES,
            "priorities": vocabulary.PRIORITIES,
            "categories": list(categories_mod.all_categories(settings.vault_path)),
        },
    )


@app.get("/api/notes")
def api_notes(
    project: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, object]]:
    settings = get_settings()
    rows = []
    for p in list_notes(settings.vault_path):
        note = Note.from_markdown(p.read_text(encoding="utf-8"))
        if project and (note.project or "").lower() != project.lower():
            continue
        if status and note.status != status:
            continue
        if category and note.category != category:
            continue
        rows.append(_summarize(note, settings.vault_path, p))
    rows.sort(key=lambda r: r["created"], reverse=True)
    return rows


def _note_detail(note: Note, vault_root: Path, path: Path) -> Dict[str, object]:
    d = _summarize(note, vault_root, path)
    d["related"] = note.related
    d["source"] = note.source
    d["language"] = note.language
    d["body"] = note.body
    return d


@app.get("/api/notes/{note_path:path}")
def api_get_note(note_path: str) -> Dict[str, object]:
    settings = get_settings()
    try:
        note = read_note(settings.vault_path, note_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _note_detail(note, settings.vault_path, Path(settings.vault_path) / note_path)


@app.get("/panel/note/{note_path:path}")
def panel_note(request: Request, note_path: str) -> Response:
    settings = get_settings()
    from . import vocabulary

    try:
        note = read_note(settings.vault_path, note_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    ui = ui_strings(settings.language)
    return _templates.TemplateResponse(
        request,
        "note.html",
        {
            "request": request,
            "ui": ui,
            "note_path": note_path,
            "note": note,
            "projects": list_projects(settings.vault_path),
            "statuses": vocabulary.STATUSES,
            "priorities": vocabulary.PRIORITIES,
            "categories": list(categories_mod.all_categories(settings.vault_path)),
        },
    )


@app.get("/panel/project/{slug}")
def panel_project(request: Request, slug: str) -> Response:
    settings = get_settings()
    from collections import Counter

    from . import vocabulary

    rows = []
    for p in list_notes(settings.vault_path):
        note = Note.from_markdown(p.read_text(encoding="utf-8"))
        if (note.project or "") == slug:
            rows.append(_summarize(note, settings.vault_path, p))
    by_status = Counter(r["status"] for r in rows)
    by_category = Counter(r["category"] for r in rows)
    ui = ui_strings(settings.language)
    return _templates.TemplateResponse(
        request,
        "project.html",
        {
            "request": request,
            "ui": ui,
            "slug": slug,
            "notes": sorted(rows, key=lambda r: r["created"], reverse=True),
            "by_status": dict(by_status),
            "by_category": dict(by_category),
            "total": len(rows),
            "statuses": vocabulary.STATUSES,
        },
    )


@app.get("/panel/project/{slug}/board")
def panel_board(request: Request, slug: str) -> Response:
    settings = get_settings()
    ui = ui_strings(settings.language)
    lang = settings.language
    statuses = vocab_mod.all_statuses(settings.vault_path)
    priorities = vocab_mod.all_priorities(settings.vault_path)
    cats = board_order.get_order(
        settings.vault_path, slug, list(categories_mod.all_categories(settings.vault_path))
    )

    notes = []
    for p in list_notes(settings.vault_path):
        note = Note.from_markdown(p.read_text(encoding="utf-8"))
        if (note.project or "") != slug:
            continue
        notes.append(
            {
                "path": str(p.relative_to(settings.vault_path)),
                "title": note.title,
                "status": note.status,
                "priority": note.priority,
                "category": note.category,
                "subcategory": note.subcategory,
            }
        )

    def _labels(entries: list[dict]) -> dict:
        return {e["key"]: e.get(f"label_{lang}") or e["key"] for e in entries}

    def _colors(entries: list[dict]) -> dict:
        return {e["key"]: e.get("color") or "#9aa0aa" for e in entries}

    def _symbols(entries: list[dict]) -> dict:
        return {e["key"]: e.get("symbol") or "o" for e in entries}

    return _templates.TemplateResponse(
        request,
        "board.html",
        {
            "request": request,
            "ui": ui,
            "slug": slug,
            "notes": notes,
            "statuses": statuses,
            "priorities": priorities,
            "categories": cats,
            "status_labels": _labels(statuses),
            "priority_labels": _labels(priorities),
            "status_colors": _colors(statuses),
            "priority_colors": _colors(priorities),
            "status_symbols": _symbols(statuses),
            "priority_symbols": _symbols(priorities),
        },
    )


class BoardMove(BaseModel):
    category: str = Field(..., min_length=1)
    direction: int = Field(..., ge=-1, le=1)


@app.post("/api/board/{slug}/move")
def api_board_move(slug: str, req: BoardMove) -> Dict[str, object]:
    settings = get_settings()
    default = list(categories_mod.all_categories(settings.vault_path))
    order = board_order.move(settings.vault_path, slug, req.category, req.direction, default)
    return {"order": order}


@app.get("/api/export")
def api_export(fmt: str = "json", project: Optional[str] = None) -> Response:
    from .export import generate

    settings = get_settings()
    fmt = fmt.lower()
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=422, detail="format must be 'json' or 'csv'")
    media = "application/json" if fmt == "json" else "text/csv"
    payload = generate(settings.vault_path, fmt, project)
    return Response(content=payload, media_type=media)


@app.get("/api/search")
def api_search(q: str, k: int = 5) -> List[Dict[str, object]]:
    from .llm import LLMClient, LLMError
    from .search import SearchError, search

    settings = get_settings()
    try:
        client = LLMClient(settings.llm_config, settings.llm_model)
        hits = search(settings.vault_path, client, q, k=k)
    except (LLMError, SearchError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [{"path": h.path, "title": h.title, "score": h.score} for h in hits]


@app.patch("/api/notes/{note_path:path}", response_model=CaptureResponse)
def api_update_note(note_path: str, req: UpdateRequest) -> CaptureResponse:
    settings = get_settings()
    try:
        note = update_note(
            settings.vault_path,
            note_path,
            title=req.title,
            status=req.status,
            priority=req.priority,
            category=req.category,
            subcategory=req.subcategory,
            project=req.project,
            body=req.body,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CaptureResponse(
        ok=True,
        path=note_path,
        title=note.title,
        type=note.type,
        category=note.category,
        subcategory=note.subcategory,
    )


@app.delete("/api/notes/{note_path:path}")
def api_delete_note(note_path: str) -> Dict[str, object]:
    settings = get_settings()
    try:
        removed = delete_note(settings.vault_path, note_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Note not found.")
    return {"ok": True, "path": note_path}


@app.delete("/api/projects/{slug}")
def api_delete_project(slug: str) -> Dict[str, object]:
    settings = get_settings()
    try:
        count = delete_project(settings.vault_path, slug)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "slug": slug, "notes_deleted": count}


@app.delete("/api/categories/{name}")
def api_delete_category(name: str) -> Dict[str, object]:
    settings = get_settings()
    try:
        removed = categories_mod.remove(settings.vault_path, name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Category not found.")
    return {"ok": True, "slug": name}


class VocabEntry(BaseModel):
    key: str = Field(..., min_length=1)
    label_en: Optional[str] = None
    label_pl: Optional[str] = None
    color: Optional[str] = None


@app.get("/api/vocab")
def api_vocab() -> Dict[str, object]:
    settings = get_settings()
    return {
        "statuses": vocab_mod.all_statuses(settings.vault_path),
        "priorities": vocab_mod.all_priorities(settings.vault_path),
    }


@app.post("/api/statuses")
def api_add_status(req: VocabEntry) -> Dict[str, object]:
    try:
        slug = vocab_mod.add_status(
            get_settings().vault_path, req.key, req.label_en, req.label_pl, req.color
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"key": slug}


@app.delete("/api/statuses/{key}")
def api_delete_status(key: str) -> Dict[str, object]:
    try:
        removed = vocab_mod.remove(get_settings().vault_path, "statuses", key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Status not found.")
    return {"ok": True}


@app.post("/api/priorities")
def api_add_priority(req: VocabEntry) -> Dict[str, object]:
    try:
        slug = vocab_mod.add_priority(
            get_settings().vault_path, req.key, req.label_en, req.label_pl, req.color
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"key": slug}


@app.delete("/api/priorities/{key}")
def api_delete_priority(key: str) -> Dict[str, object]:
    try:
        removed = vocab_mod.remove(get_settings().vault_path, "priorities", key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Priority not found.")
    return {"ok": True}


@app.get("/api/projects")
def api_projects() -> List[str]:
    return list_projects(get_settings().vault_path)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)


@app.post("/api/projects")
def api_create_project(req: ProjectCreate) -> Dict[str, object]:
    try:
        slug = create_project(get_settings().vault_path, req.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"name": req.name, "slug": slug}


@app.get("/api/categories")
def api_categories() -> Dict[str, object]:
    settings = get_settings()
    return categories_mod.all_categories(settings.vault_path)


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    subcategories: List[str] = Field(default_factory=list)
    description: Optional[str] = None


@app.post("/api/categories")
def api_create_category(req: CategoryCreate) -> Dict[str, object]:
    settings = get_settings()
    try:
        slug = categories_mod.add(
            settings.vault_path, req.name, req.subcategories, req.description
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "name": req.name,
        "slug": slug,
        "subcategories": req.subcategories,
        "description": req.description or "",
    }


@app.post("/api/capture", response_model=CaptureResponse)
def api_capture(req: CaptureRequest) -> CaptureResponse:
    settings = get_settings()
    try:
        if req.ai:
            result = capture(req.text, settings)
        else:
            result = capture_manual(
                req.text,
                settings,
                project=req.project,
                category=req.category,
                subcategory=req.subcategory,
                status=req.status,
                priority=req.priority,
                tags=req.tags,
            )
    except CaptureError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    note = result.note
    return CaptureResponse(
        ok=True,
        path=str(result.path),
        title=note.title,
        type=note.type,
        category=note.category,
        subcategory=note.subcategory,
    )
