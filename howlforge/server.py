"""FastAPI app: health check + an HTTP capture endpoint.

The HTTP endpoint lets you test the capture pipeline without Telegram
(``curl -X POST localhost:8000/api/capture -d '{"text": "..."}``). It shares the
same :func:`howlforge.capture.capture` service as the Telegram bot.

Run with::

    uvicorn howlforge.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .capture import CaptureError, capture, capture_manual
from .config import get_settings
from .schema import Note
from .vault import create_project, list_notes, list_projects, update_note

app = FastAPI(title="HowlForge", version="0.1.0")
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


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
    return _templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "notes": rows,
            "projects": projects,
            "statuses": vocabulary.STATUSES,
            "priorities": vocabulary.PRIORITIES,
            "categories": list(vocabulary.CATEGORIES),
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
