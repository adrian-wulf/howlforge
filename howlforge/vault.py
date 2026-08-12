"""Vault operations: bootstrap the folder layout and persist notes.

The vault is a plain folder of Markdown files. This module owns the filesystem
side: creating the layout, slugifying filenames, and writing notes without
clobbering existing files.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .schema import Note, destination_path

logger = logging.getLogger(__name__)

# Top-level folders mirrored in vault_template/. Keep in sync.
LAYOUT: list[str] = [
    "00 Inbox",
    "10 Projects",
    "20 Systems",
    "30 Assets & References",
    "40 Inspiration",
    "90 Archive",
    "_MOC",
]

# Project-scoped subfolders, created on demand inside a project.
PROJECT_SUBFOLDERS = ["GDD", "Mechanics", "Art", "Audio", "Systems"]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()


def ensure_vault(vault_root: Path) -> Path:
    """Create the vault folder layout if missing; return the root path."""
    root = Path(vault_root)
    root.mkdir(parents=True, exist_ok=True)
    for folder in LAYOUT:
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


def project_folder(vault_root: Path, project: str) -> Path:
    """Return (and create) the folder for a project slug."""
    slug = _slugify(project)
    folder = Path(vault_root) / "10 Projects" / slug
    folder.mkdir(parents=True, exist_ok=True)
    for sub in PROJECT_SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder


def list_projects(vault_root: Path) -> list[str]:
    """Return the names (slugs) of all project folders in the vault."""
    root = Path(vault_root) / "10 Projects"
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
    )


def create_project(vault_root: Path, name: str) -> str:
    """Create a project folder and return its slug. No-op if it exists."""
    slug = _slugify(name)
    if not slug:
        raise ValueError("Project name cannot be empty.")
    project_folder(vault_root, slug)
    return slug


def write_note(note: Note, vault_root: Path) -> Path:
    """Write a note into the vault, never overwriting an existing file.

    If the target filename already exists, a numeric suffix is appended. Returns
    the absolute path of the written file.
    """
    root = ensure_vault(vault_root)
    folder = destination_path(note, root)
    folder.mkdir(parents=True, exist_ok=True)
    slug = _slugify(note.title) or "untitled"
    path = folder / f"{slug}.md"
    counter = 2
    while path.exists():
        path = folder / f"{slug}-{counter}.md"
        counter += 1
    path.write_text(note.to_markdown(), encoding="utf-8")
    logger.info("Wrote note -> %s", path)
    return path


def list_notes(vault_root: Path) -> list[Path]:
    """Return all markdown note files in the vault (recursively)."""
    root = Path(vault_root)
    if not root.exists():
        return []
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.is_file() and ".obsidian" not in p.parts and ".trash" not in p.parts
    )


def read_note(vault_root: Path, relative_path: str) -> Note:
    """Read a single note by its vault-relative path."""
    root = Path(vault_root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path escapes the vault.")
    if not path.exists():
        raise FileNotFoundError(f"No such note: {relative_path}")
    return Note.from_markdown(path.read_text(encoding="utf-8"))


def update_note(
    vault_root: Path,
    relative_path: str,
    *,
    title: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    project: Optional[str] = None,
    body: Optional[str] = None,
) -> Note:
    """Update select fields of a note in place and return the updated note.

    Only ``status`` and ``priority`` are validated against the vocabulary; the
    others are applied as-is so free text (title/body) is not restricted. When
    ``project`` changes, the note is moved to the new project folder.
    """
    root = Path(vault_root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path escapes the vault.")
    if not path.exists():
        raise FileNotFoundError(f"No such note: {relative_path}")

    note = Note.from_markdown(path.read_text(encoding="utf-8"))
    from . import vocab as vocab_mod

    valid_statuses = vocab_mod.status_keys(root)
    valid_priorities = vocab_mod.priority_keys(root)
    project_changed = False
    if project is not None:
        new_slug = _slugify(project)
        if (note.project or "") != new_slug:
            note.project = new_slug or None
            project_changed = True
    if status is not None:
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        note.status = status
    if priority is not None:
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority: {priority}")
        note.priority = priority
    if title is not None:
        note.title = title.strip() or note.title
    from . import categories as categories_mod

    if category is not None and category in categories_mod.all_categories(root):
        note.category = category
    if subcategory is not None:
        note.subcategory = subcategory
    if body is not None:
        note.body = body
    note.updated = _now_iso()

    if project_changed:
        folder = destination_path(note, root)
        folder.mkdir(parents=True, exist_ok=True)
        new_path = folder / path.name
        counter = 2
        while new_path.exists():
            new_path = folder / f"{path.stem}-{counter}{path.suffix}"
            counter += 1
        path.rename(new_path)
        path = new_path

    path.write_text(note.to_markdown(), encoding="utf-8")
    logger.info("Updated note -> %s", path)
    return note


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def delete_note(vault_root: Path, relative_path: str) -> bool:
    """Delete a note by its vault-relative path. Returns True if it was removed."""
    root = Path(vault_root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path escapes the vault.")
    if not path.exists() or not path.is_file():
        return False
    path.unlink()
    logger.info("Deleted note -> %s", path)
    return True


def delete_project(vault_root: Path, slug: str) -> int:
    """Delete a project folder and all notes inside it. Returns the number of
    removed note files."""
    import shutil

    root = Path(vault_root).resolve()
    slug = _slugify(slug)
    folder = (root / "10 Projects" / slug).resolve()
    if not folder.is_relative_to(root):
        raise ValueError("Project path escapes the vault.")
    if not folder.exists():
        return 0
    count = len([p for p in folder.rglob("*.md") if p.is_file()])
    shutil.rmtree(folder)
    logger.info("Deleted project '%s' (%d notes)", slug, count)
    return count
