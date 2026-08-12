"""Vault operations: bootstrap the folder layout and persist notes.

The vault is a plain folder of Markdown files. This module owns the filesystem
side: creating the layout, slugifying filenames, and writing notes without
clobbering existing files.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

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
