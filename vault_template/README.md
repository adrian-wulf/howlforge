# Vault layout

A HowlForge vault is a plain folder of Markdown notes. Copy or point
`HOWLFORGE_VAULT_PATH` at this layout (or let `howlforge init` create it).

```
vault/
|-- 00 Inbox/                raw captures waiting to be triaged
|-- 10 Projects/             one folder per project (GDD, Mechanics, Art, Audio by default)
|-- 20 Systems/              reusable systems and patterns
|-- 30 Assets & References/  reusable assets and research links
|-- 40 Inspiration/          mood, influences, references
|-- 90 Archive/              rejected / shipped / no longer active
`-- _MOC/                    Maps of Content (incl. AI synthesis digests)
```

Every note carries YAML frontmatter against the controlled vocabulary in
`howlforge/vocabulary.py`:

```yaml
---
title: Weekly review template
type: note              # idea | mechanic | system | asset | reference | ...
project: work
category: production
subcategory: tasks
status: raw               # raw | processed | prototype | implemented | rejected | archived
priority: high            # critical | high | medium | low | backlog
tags: [review, template]
related: []
source: telegram
language: pl              # pl | en
created: 2026-08-12T19:30Z
---
```

`howlforge init` regenerates this layout. Keep the numbers for stable sorting.
The built-in vocabulary in `howlforge/vocabulary.py` is game-dev flavored;
categories, statuses and priorities can be extended per vault from the panel or bot
(`<vault>/.howlforge/categories.json` and `vocab.json`).
