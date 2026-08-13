"""Export notes to JSON or CSV.

Produces machine-readable views of the vault so notes can be loaded by
spreadsheets, scripts, game engines or any other tooling:
* ``JSON`` - an array of note objects (with tags as a list).
* ``CSV`` - flat rows with a subset of scalar fields.

Both support optional ``project`` filtering. ``generate`` returns the payload as a
string for a given format; helpers ``export_json`` and ``export_csv`` write a file.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Dict, List, Optional

from .schema import Note
from .vault import list_notes

# CSV-friendly columns (scalar only; no tags/related).
CSV_COLUMNS = [
    "path",
    "title",
    "type",
    "project",
    "category",
    "subcategory",
    "status",
    "priority",
    "source",
    "language",
    "generated",
    "created",
    "updated",
]


def _records(vault_root: Path, project: Optional[str]) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for p in list_notes(vault_root):
        note = Note.from_markdown(p.read_text(encoding="utf-8"))
        if project and (note.project or "").lower() != project.lower():
            continue
        records.append(
            {
                "path": str(p.relative_to(vault_root)),
                "title": note.title,
                "type": note.type,
                "project": note.project or "",
                "category": note.category,
                "subcategory": note.subcategory,
                "status": note.status,
                "priority": note.priority,
                "tags": note.tags,
                "related": note.related,
                "source": note.source,
                "language": note.language,
                "generated": note.generated,
                "created": note.created,
                "updated": note.updated,
                "body": note.body,
            }
        )
    return records


def generate(
    vault_root: Path,
    fmt: str = "json",
    project: Optional[str] = None,
) -> str:
    """Return the export payload for ``fmt`` (``json`` or ``csv``) as a string."""
    records = _records(vault_root, project)
    if fmt == "json":
        return json.dumps(records, ensure_ascii=False, indent=2)
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)
        return buf.getvalue()
    raise ValueError(f"Unsupported format: {fmt!r}")


def export_file(
    vault_root: Path,
    out: Path,
    fmt: Optional[str] = None,
    project: Optional[str] = None,
) -> Path:
    """Write an export file. ``fmt`` defaults to ``out`` suffix or ``json``."""
    fmt = (fmt or out.suffix.lstrip(".") or "json").lower()
    out.write_text(generate(vault_root, fmt, project), encoding="utf-8")
    return out
