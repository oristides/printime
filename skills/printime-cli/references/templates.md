# Templates and Markdown

**This file contains:** template field reference, frontmatter keys, inline QR / mermaid fence syntax, markdown table limits and wrapping rules.

Template auto-detection: [SKILL.md](../SKILL.md) §4. ASCII font list: SKILL.md §7 / `printime ascii-fonts`.

## Template Overview

| Template | Use |
| -------- | --- |
| `note` | Title, auto datetime, body, priority, tags |
| `document` | Mixed markdown, mermaid, inline QR |
| `checklist` | Checkbox list + auto datetime |
| `diagram` | Mermaid-only page (no print timestamp) |
| `ticket` | PDF-extracted codes |
| `agenda` | Calendar events + auto datetime |
| `task`, `jira`, `message`, `email`, `receipt`, `heading`, `equation` | Specialized layouts |

`printime list` / `printime list <name>` for full field lists.

## Frontmatter

| Field | Purpose |
| ----- | ------- |
| `template` | Force template (else auto-detect) |
| `title` | Header; else first `#` heading or filename |
| `caption` | Subtitle |
| `date` | Override auto `YYYY-MM-DD HH:MM` on `note`, `checklist`, `message`, `agenda` |
| `priority`, `tags`, `due_date`, `sender`, `subject`, … | Template-specific |

## Template Fields

### `note`

`title`, `caption`, `date`, `content`, `priority`, `tags`

### `checklist`

`title`, `caption`, `date`, `content`, `items`

```bash
printime print --template checklist --title "Market" \
  --items "Milk|Bread::x|Eggs|Butter|Coffee::x" --preview
```

Separator: `|`. Checked: `::x`, `::checked`, `::done`.

### `message`

`title`, `caption`, `date`, `content`

### `email`

`subject`, `sender`, `to`, `cc`, `reply_to`, `date`, `body`, `content`, `labels`, `message_id`

YAML `from:` → `sender`. `to` / `cc`: string or list.

### `agenda`

`title`, `caption`, `date`, `days`, `empty_message`, `source` — normally built by `printime agenda`, not hand-authored. Events: `time`, `title`, `location`, `notes`.

## Inline QR Fence

````markdown
```qr --qr-size 10 --center --show-link
https://example.com
```
````

Flags: `--qr-size` (4–12), `--center`, `--show-link`.

## ASCII Art Fence

````markdown
```slant --center
hello
```
````

Public fonts: `pagga`, `avatar`, `bulbhead`, `banner`, `slant`. Flags: `--center`, `--api-fallback`, `--strict`. Details: SKILL.md §7.

## Mermaid Fence

````markdown
```mermaid
flowchart TD
  A --> B
```
````

Plain fences starting with `graph` / `flowchart` are also detected (Anytype exports).

## Context Files

JSON/YAML via `--template` + `--file` or positional context file. Rich markdown: prefer `.md`.

## Table Limits (48-column paper)

Renderer strips outer pipes, ignores separator rows, normalizes `<br>`, wraps cells to paper width.

| Columns | Guidance |
| ------- | -------- |
| 2 | Best; cells ~18–22 chars |
| 3 | Default sweet spot; ~12–14 chars |
| 4 | Dashboard size; ~8–10 chars |
| 5 | Max practical; short values only |
| 6+ | Renders but unreadable |

- Long cell text wraps under the same column.
- Long URLs/IDs: split to fit; use link QR for scannable URLs.
- Alignment markers ignored; output left-aligned.
- Header row bold when standard `|---|` separator present.
- Not supported: nested tables, merged cells, multiline cells, HTML tables.

Inline markdown in cells is stripped to plain text (`**bold**`, links, etc.).

Use tables for short structured data; bullets/checklists for sentence-length rows.
