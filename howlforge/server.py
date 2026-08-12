"""FastAPI app: health check + an HTTP capture endpoint.

The HTTP endpoint lets you test the capture pipeline without Telegram
(``curl -X POST localhost:8000/api/capture -d '{"text": "..."}``). It shares the
same :func:`howlforge.capture.capture` service as the Telegram bot.

Run with::

    uvicorn howlforge.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .capture import CaptureError, capture
from .config import get_settings

app = FastAPI(title="HowlForge", version="0.1.0")


class CaptureRequest(BaseModel):
    text: str = Field(..., min_length=1)


class CaptureResponse(BaseModel):
    ok: bool
    path: str
    title: str
    type: str
    category: str
    subcategory: str


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/capture", response_model=CaptureResponse)
def api_capture(req: CaptureRequest) -> CaptureResponse:
    settings = get_settings()
    try:
        result = capture(req.text, settings)
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
