"""The note model and YAML frontmatter serialisation.

A note is a Markdown file whose YAML frontmatter follows a fixed schema. The schema
is the contract between the AI pipeline and consumers (Obsidian Dataview, web panel,
CLI), so it must stay stable and validated.

Canonical field order is defined in ``Note.field_order`` so files stay consistent
and diffs are clean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Dict, List, Optional

import frontmatter
import yaml

from . import vocabulary


@dataclass
class Note:
    type: str = "idea"
    project: Optional[str] = None
    category: str = "misc"
    subcategory: str = "none"
    status: str = "raw"
    priority: str = "backlog"
    tags: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    source: str = "manual"
    language: str = "en"
    generated: bool = False
    created: str = field(default_factory=lambda: _now_iso())
    updated: str = field(default_factory=lambda: _now_iso())
    title: str = "Untitled"
    body: str = ""

    # Canonical serialisation order (class-level, not a per-instance field).
    field_order: ClassVar[List[str]] = [
        "type",
        "project",
        "category",
        "subcategory",
        "status",
        "priority",
        "tags",
        "related",
        "source",
        "language",
        "generated",
        "created",
        "updated",
    ]

    def validate(
        self,
        categories: Optional[Dict[str, List[str]]] = None,
        statuses: Optional[List[str]] = None,
        priorities: Optional[List[str]] = None,
    ) -> List[str]:
        """Return a list of human-readable errors; empty means valid.

        ``categories``, ``statuses`` and ``priorities`` are the merged vocab (built-in
        + custom). When omitted only the built-in vocabulary is used.
        """
        cats = categories or vocabulary.CATEGORIES
        status_keys = statuses or vocabulary.STATUSES
        priority_keys = priorities or vocabulary.PRIORITIES
        errors: List[str] = []
        if not vocabulary.is_valid_type(self.type):
            errors.append(f"type: '{self.type}' is not allowed")
        if self.category not in cats:
            errors.append(f"category: '{self.category}' is not allowed")
        if self.subcategory not in cats.get(self.category, []):
            errors.append(
                f"subcategory '{self.subcategory}' is not allowed for category '{self.category}'"
            )
        if self.status not in status_keys:
            errors.append(f"status: '{self.status}' is not allowed")
        if self.priority not in priority_keys:
            errors.append(f"priority: '{self.priority}' is not allowed")
        if not self.title.strip():
            errors.append("title is empty")
        return errors

    @property
    def is_valid(self) -> bool:
        return not self.validate()

    def to_markdown(self) -> str:
        """Serialise to Markdown with YAML frontmatter."""
        meta: Dict[str, object] = {}
        for key in self.field_order:
            value = getattr(self, key)
            # Drop empty optional fields to keep files tidy.
            if value is None or value == [] or value == "":
                continue
            if key == "generated" and value is False:
                continue
            meta[key] = value

        fm = frontmatter.Post(self.body, **meta)
        fm["title"] = self.title
        # Reorder: title first, then canonical order.
        ordered: Dict[str, object] = {"title": self.title}
        for key in self.field_order:
            if key in meta:
                ordered[key] = meta[key]
        payload = yaml.safe_dump(
            ordered, allow_unicode=True, sort_keys=False, default_flow_style=None
        )
        return f"---\n{payload}---\n{self.body.rstrip()}\n"

    @classmethod
    def from_markdown(cls, text: str) -> "Note":
        post = frontmatter.loads(text)
        known = {k for k in cls.field_order}
        data = {k: v for k, v in post.metadata.items() if k in known}
        data["title"] = post.metadata.get("title", post.get("title", "Untitled"))
        data["body"] = post.content
        return cls(**data)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def destination_path(note: Note, vault_root: Path) -> Path:
    """Compute the vault path for a note, creating project folders as needed."""
    pattern = vocabulary.destination_for(note.type)
    slug = (note.project or "").strip()
    folder = pattern.format(project=slug) if slug else pattern.replace("/{project}", "")
    return Path(vault_root) / folder
