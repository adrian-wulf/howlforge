"""Controlled vocabulary for the vault.

The whole system depends on this staying stable. Keys are **English tokens** and
never translated, so Dataview queries, filters and the web panel can rely on them.
Human-readable labels live in :mod:`howlforge.i18n`.

Do not add free-form categories here. If you need a new one, extend this list and
regenerate the vault so existing notes stay consistent.
"""

from __future__ import annotations

from typing import Dict, List, Literal

# ---- Top-level note types (map to destination folders) ---------------------
NOTE_TYPES: List[str] = [
    "idea",        # raw spark, starts in Inbox
    "mechanic",    # a game mechanic / rule
    "system",      # a coherent system built from mechanics
    "asset",       # a reusable asset (art, audio, model, script)
    "reference",   # a reference or research link
    "inspiration", # inspiration / mood / influence
    "gdd",         # game design document section / page
    "synthesis",   # AI-generated digest (append-only, never overwrites source)
    "note",        # generic note
]

# ---- Status lifecycle ------------------------------------------------------
# raw -> processed -> prototype -> implemented (or rejected / archived)
STATUSES: List[str] = [
    "raw",
    "processed",
    "prototype",
    "implemented",
    "rejected",
    "archived",
]

# ---- Priorities ------------------------------------------------------------
PRIORITIES: List[str] = [
    "critical",
    "high",
    "medium",
    "low",
    "backlog",
]

# ---- Capture sources -------------------------------------------------------
SOURCES: List[str] = [
    "telegram",
    "manual",
    "web",
    "voice",
    "image",
    "api",
    "import",
]

# ---- Categories and their allowed subcategories ----------------------------
# Subcategory may be "none" (no subcategory) or one of the listed tokens.
CATEGORIES: Dict[str, List[str]] = {
    "art": [
        "style", "concept", "character", "environment",
        "ui", "animation", "vfx", "color", "none",
    ],
    "gameplay": ["loop", "progression", "difficulty", "controls", "combat", "puzzle", "none"],
    "mechanics": ["economy", "systems", "inventory", "crafting", "farming", "combat", "none"],
    "audio": ["music", "sfx", "ambient", "voice", "none"],
    "story": ["plot", "lore", "characters", "dialogue", "worldbuilding", "none"],
    "systems": ["save", "modding", "procedural", "tech", "none"],
    "technical": ["engine", "performance", "netcode", "tooling", "architecture", "none"],
    "production": ["scope", "roadmap", "pipeline", "tasks", "none"],
    "monetization": ["pricing", "revenue", "dlc", "none"],
    "marketing": ["wishlists", "store", "trailer", "community", "none"],
    "misc": ["none"],
}

Language = Literal["pl", "en"]
LANGUAGES: List[str] = ["pl", "en"]

# ---- Destination folder per note type --------------------------------------
# Relative to vault root. Project-scoped types insert the project slug.
def destination_for(note_type: str) -> str:
    """Return the top-level vault folder for a note type (with {project} marker)."""
    mapping = {
        "idea": "00 Inbox",
        "mechanic": "10 Projects/{project}/Mechanics",
        "system": "20 Systems",
        "asset": "10 Projects/{project}/Assets",
        "reference": "30 Assets & References",
        "inspiration": "40 Inspiration",
        "gdd": "10 Projects/{project}/GDD",
        "synthesis": "_MOC",
        "note": "00 Inbox",
    }
    return mapping[note_type]


def is_valid_status(value: str) -> bool:
    return value in STATUSES


def is_valid_priority(value: str) -> bool:
    return value in PRIORITIES


def is_valid_type(value: str) -> bool:
    return value in NOTE_TYPES


def is_valid_category(value: str) -> bool:
    return value in CATEGORIES


def is_valid_subcategory(category: str, subcategory: str) -> bool:
    if category not in CATEGORIES:
        return False
    return subcategory in CATEGORIES[category]
