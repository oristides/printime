# Templates and Markdown

Printime renders Jinja2 templates from CLI flags, markdown frontmatter, JSON/YAML context files, Anytype pages, Google Calendar events, Keep notes, or ticket PDF extraction.

## List Templates

```bash
printime list
printime list --verbose
printime list document
```

Prefer templates over raw `--text`: templates provide a title block, automatic datetime when supported, and predictable receipt layout.

Common templates:

| Template | Use |
| -------- | --- |
| `note` | Personal note with title, automatic datetime, body, priority, tags. |
| `document` | Mixed markdown, headings, checkboxes, mermaid, inline QR. |
| `checklist` | Checkbox list with automatic datetime. |
| `diagram` | Mermaid diagram page. |
| `ticket` | Extracted ticket PDF QR/barcode content. |
| `agenda` | Google Calendar agenda with automatic datetime, locations, and notes. |
| `task`, `jira`, `message`, `receipt`, `heading`, `equation` | Specialized layouts. |

## Markdown File

````markdown
---
title: Login Flow
caption: Happy path only
template: document
---

# Steps

- [ ] Open app
- [x] Login

```mermaid
graph TD
  A --> B
```

```qr --qr-size 10 --center
"https://example.com"
```
````

Print it:

```bash
printime print login-flow.md --preview
```

## Frontmatter

| Field | Purpose |
| ----- | ------- |
| `template` | Force a template; otherwise Printime auto-detects. |
| `title` | Header title. Falls back to first heading or file name. |
| `caption` | Subtitle under title. |
| `date` | Overrides the automatic `YYYY-MM-DD HH:MM` printed by `note`, `checklist`, `message`, and `agenda`. |
| `priority`, `tags`, `due_date`, etc. | Passed to template-specific fields. |

## Important Template Fields

### `note`

Fields: `title`, `caption`, `date`, `content`, `priority`, `tags`.

```bash
printime print --template note --title "Today" --content "Ship docs" --preview
```

### `checklist`

Fields: `title`, `caption`, `date`, `content`, `items`.

```yaml
title: Shopping
items:
  - text: Milk
    checked: false
```

```bash
printime print --template checklist --file shopping.yaml --preview
```

### `message`

Fields: `title`, `caption`, `date`, `content`.

```bash
printime print --template message --title "Alert" --content "Printer ready" --preview
```

### `agenda`

Fields: `title`, `caption`, `date`, `days`, `empty_message`, `source`.

Normally use the command instead of building context manually:

```bash
printime agenda --today --preview
printime agenda --days 7 --preview
printime agenda --next-week --preview
```

Each event can include `time`, `title`, `location`, and `notes`.

## Auto Detection

| Content | Template |
| ------- | -------- |
| Body/checklist plus mermaid or inline QR | `document` |
| Mermaid only | `diagram` |
| Checkboxes only | `checklist` |
| Plain prose | `note` |
| Positional `.pdf` | `ticket` |

## Inline QR Blocks

````markdown
```qr --qr-size 10 --center --show-link
"https://example.com"
```
````

Flags:

- `--qr-size`: module size 4-12.
- `--center`: center the QR on paper.
- `--show-link`: print text below the QR.

## Tables

Markdown tables work in `.md` files, `--markdown --text`, and Anytype pages. The renderer removes raw outer pipes, ignores separator rows, normalizes Anytype `<br>` markup, and wraps cells to receipt width.

```markdown
| Metric | Owner | Status | Next |
| --- | --- | --- | --- |
| Activation | Ana | Green | Watch signups |
| Churn | Bob | Yellow | Call accounts |
| Cash | Lia | Red | Cut spend |
```

```bash
printime print examples/oriel-mandates.md --preview
printime print --markdown --text $'## Review\n\n| Area | DRI | Risk | Due | Note |\n| --- | --- | --- | --- | --- |\n| API | Ana | Low | Mon | Ship |\n| Billing | Bob | Medium | Tue | Needs review |' --preview
```

### Table limits and recommendations

Printime targets 48-character receipt paper. The table renderer removes raw outer pipes, ignores separator rows, normalizes Anytype `<br>` line breaks, and wraps cells so every printed line stays within the paper width.

Recommended table sizes:

- 2 columns: best readability; cells around 18-22 chars.
- 3 columns: best default; cells around 12-14 chars.
- 4 columns: useful dashboard size; cells around 8-10 chars.
- 5 columns: maximum practical size; use only for dense summaries with short values.

Limits:

- More than 5 columns is not recommended. It renders, but cells become too narrow to scan.
- Long cell text wraps onto continuation lines under the same column.
- Very long unbroken words, URLs, or IDs are split to fit; use QR/link QR output for URLs.
- Markdown alignment markers are accepted but not preserved; output is left-aligned.
- Header cells are bold when the table has a standard separator row.
- Nested tables, merged cells, multiline markdown inside one cell, and HTML table tags are not supported.

Use tables for short structured data. Use checklists or bullet lists for sentence-length rows.

Inline cell markdown is cleaned: `**P0**`, `` `Done` ``, `[Spec](https://...)`, and `### Owner` print as readable text.

## Mermaid Blocks

````markdown
```mermaid
flowchart TD
  A --> B
```
````

Plain code fences that start with `graph TD`, `flowchart`, or similar Mermaid syntax are also detected, which helps with Anytype exports.

## Context Files

JSON/YAML files can be printed through a template:

```bash
printime print --template note --file note.yaml --preview
printime print context.json --template receipt --preview
```

For rich markdown, prefer a `.md` file unless a structured context file is clearer.
