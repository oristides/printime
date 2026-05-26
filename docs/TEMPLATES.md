# Templates

Printime renders **Jinja2 templates** (`.j2` files in `templates/`) using data from markdown frontmatter, inline CLI flags, or JSON/YAML files. Prefer templates over raw `--text` for user-facing paper because templates provide titles, structured fields, and consistent layout.

List available templates:

```bash
printime list
printime list document    # fields for one template
```

## Markdown-first workflow

Write a `.md` file with optional YAML frontmatter:

````markdown
---
title: Login Flow
caption: Happy path only
---

# Headin1
## heading 2
### heading 3

Body text here. Left-aligned by default.

- [ ] Milk
- [x] Bread

```mermaid
graph TD
  A --> B
```

```qr --qr-size 10 --center
"https://example.com"
```

```slant --center
hello world
```
````

Print:

```bash
printime print my-file.md --preview
printime print examples/diagram_flow.md --preview
```

See `examples/diagram_flow.md` for a full mixed-content page.

### Frontmatter fields

| Field | Purpose |
| ----- | ------- |
| `template` | Force a template (`note`, `document`, `checklist`, …). Auto-detected if omitted. |
| `title` | Header title (between `====` lines). Falls back to `# Heading` or filename. |
| `caption` | Subtitle under title in the header block (not a diagram label). |
| `date` | Override the automatic `YYYY-MM-DD HH:MM` line printed by `note`, `checklist`, `message`, and `agenda`. |
| Other keys | Map to template variables (`priority`, `tags`, `due_date`, …). |

### Auto template detection

| Content | Template |
| ------- | -------- |
| Mermaid and/or inline QR **plus** body text or checkboxes | `document` |
| Mermaid only | `diagram` |
| Checkboxes only | `checklist` |
| Plain prose | `note` |

### Markdown body syntax

- `#` / `##` / `###` — heading sizes (left-aligned; use `<center>...</center>` to center)
- `- [ ]` / `- [x]` — checklist items (one line per item on paper)
- Markdown tables — rendered as compact receipt columns for preview and paper
- ` ```mermaid ` … ` ``` ` — diagram (rendered via mermaid-cli if installed)
- Plain ` ``` ` fence with `graph TD` / `flowchart` — also treated as mermaid (Anytype export)
- ` ```qr [flags] ` … ` ``` ` — inline QR block
- ` ```ascii font=slant [flags] ` … ` ``` ` or direct ` ```slant ` fences — receipt-safe ASCII art

### Tables

Markdown tables work in `.md` files, `--markdown --text`, and Anytype pages. Anytype table markup with `<br>` line breaks is normalized before rendering.

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

#### Table limits and recommendations

Printime renders tables for 48-character receipt paper. The renderer removes raw outer pipes, ignores separator rows, normalizes Anytype `<br>` line breaks, and wraps cells so every printed line stays within the paper width.

Recommended table sizes:

- 2 columns: best readability for labels and values; cells can be about 18-22 chars.
- 3 columns: best default for status tables; cells can be about 12-14 chars.
- 4 columns: good for compact dashboards; cells should be about 8-10 chars.
- 5 columns: maximum practical size; use only for dense summaries with short headers and short values.

Limits:

- More than 5 columns is not recommended on 48-character paper. It will render, but cells become too narrow to scan.
- Long cell text wraps onto continuation lines under the same column. This is acceptable for notes, but it makes dense tables taller.
- Very long unbroken words, URLs, or IDs are split to fit. Put URLs in QR blocks or link QR output instead of table cells.
- Markdown table alignment markers (`:---`, `---:`, `:---:`) are accepted but alignment is not preserved; output is left-aligned for scanability.
- Header cells are bold when the table has a standard separator row.
- Nested tables, merged cells, multiline markdown inside a single cell, and HTML table tags are not supported. Convert those to lists or multiple smaller tables.

Use tables for short structured data. Use checklists or bullet lists when rows contain sentence-length text.

Inline markdown inside cells is cleaned for paper output, so `**P0**`, `` `Done` ``, `[Spec](https://...)`, and `### Owner` become readable text.

**QR fence flags** (same as CLI):

````markdown
```qr --qr-size 10 --center --show-link
"https://example.com"
```
````

- `--qr-size` — module size 4–12 (default 8)
- `--center` — center on paper
- `--show-link` — print URL text below QR

### ASCII art fences

ASCII art works in markdown files, `--markdown --text`, and template `--content` when markdown enrichment is enabled. Use `printime ascii-fonts` to list the limited public font choices from the CLI.

````markdown
```ascii font=slant --center
hello world
```

```pagga --center
oriel
```
````

Supported public fonts are intentionally limited to the thermal-safe set:

| Font | Manual max hint | Best for |
| ---- | --------------- | -------- |
| `pagga` | ~12 chars | Compact short words |
| `avatar` | ~8 chars | Clean names and labels |
| `bulbhead` | ~7 chars | Friendly headings |
| `banner` | ~7 chars | Bold block headers |
| `slant` | ~8 chars | General short text |

Printime does not rely only on these manual limits. It renders candidate word groups, measures the widest output line, and wraps before any line exceeds the configured paper width. Local `pagga` uses pyfiglet's packaged `pagga.tlf` TOIlet font and matches the asciified API when requested as `Pagga` (the API is case-sensitive). Printime keeps the native FIGlet spacing instead of post-processing it away. For longer messages, words are grouped into multiple ASCII-art chunks. If one unbroken word is too wide, Printime splits that word into multiple fitted chunks before trying compact internal fallback fonts (`small`, `smslant`, `mini`) unless strict mode is enabled. Wider or noisy FIGlet fonts such as `shadow`, `thin`, `varsity`, `banner3`, `sub-zero`, and `the-edge` are not public options because they do not fit 48-column thermal receipts reliably.

Fence flags:

- `font=<name>` or `--font <name>` — choose a font when using the `ascii` fence.
- `--center`, `--left`, `--right` — align the rendered block.
- `--api-fallback` — try the asciified API if local `pyfiglet` rendering fails.
- `--strict` — fail instead of using a compact fallback font.

### Title header layout

When `title` (and optional `caption`) are set, they print together at the top:

```text
================================================
LOGIN FLOW
Happy path only
2026-05-25 12:21
================================================
```

Body headings (`#`, `##`) print below this block — they do not replace the frontmatter title. The datetime line appears automatically for `note`, `checklist`, `message`, and `agenda`; set `date:` only when you need to override it.

---

## document

Full page: title + caption header, styled markdown, checklists, mermaid diagram, inline QR — in source order.

**Fields:** `title`, `caption`, `content`, `items`, `mermaid`, `qr`, `segments`

**Example:** `examples/diagram_flow.md`

```bash
printime print examples/diagram_flow.md --preview
```

Used automatically when markdown mixes prose/checkboxes with mermaid or QR blocks. Also selected for rich Anytype pages.

---

## diagram

Title, rendered mermaid image, optional caption.

**Fields:** `title`, `caption`, `mermaid`, `image_path`

```bash
printime print --mermaid flow.mmd --preview
printime print diagram-only.md --preview   # markdown with only a mermaid block
```

Requires `@mermaid-js/mermaid-cli` (`mmdc` or `npx @mermaid-js/mermaid-cli`).

---

## note

Personal note with title, optional caption, automatic datetime, body, optional priority and tags.

**Fields:** `title`, `caption`, `date`, `content`, `priority`, `tags`

**Markdown example** (`examples/note.md`):

```markdown
---
template: note
priority: high
tags: [standup, team]
---

# Team Standup Notes

Daily standup discussions and sprint progress.

- Review blockers
- Plan next sprint
```

**Inline CLI:**

```bash
printime print --template note \
  --title "Quick note" \
  --content "Remember to send the report" \
  --priority high \
  --tags "work" \
  --preview
```

---

## checklist

Checkbox list for shopping lists, todos, etc. Includes automatic datetime under the title/caption.

**Fields:** `title`, `caption`, `date`, `content`, `items` (each item: `text`, `checked`)

**Markdown example** (`examples/checklist.md`):

```markdown
---
template: checklist
title: Weekly Shopping List
---

- [ ] Milk
- [x] Bread
- [ ] Eggs
```

```bash
printime print examples/checklist.md --preview
```

You do not need `template: checklist` if the file only contains checkbox lines — it is detected automatically.

---

## task

Single task with description, due date, and completion status.

**Fields:** `title`, `description`, `due_date`, `priority`, `completed`

**Markdown example** (`examples/task.md`):

```markdown
---
template: task
priority: high
due_date: 2026-05-30
completed: false
---

# Fix printer preview

Align printed output with terminal preview.
```

---

## jira

Compact Jira ticket printout.

**Fields:** `ticket_id`, `summary`, `description`, `status`, `priority`, `assignee`, `labels`

Note: use `summary` in frontmatter, or set `title` / `# Heading` — it maps to `summary` automatically.

---

## message

Short message with title, optional caption, automatic datetime, and body (simpler than `note` — no priority/tags).

**Fields:** `title`, `caption`, `date`, `content`

---

## heading

Large heading text for labels or section markers.

**Fields:** `text`, `style`

---

## receipt

Receipt-style layout with line items and totals.

**Fields:** `store_name`, `date`, `items`, `subtotal`, `tax`, `total`, `payment_method`

---

## agenda

Calendar day/week layout with automatic datetime, event times, titles, locations, and notes/details.

**Fields:** `title`, `caption`, `date`, `days`, `empty_message`, `source`

Used automatically by `printime agenda`. Each event can include `time`, `title`, `location`, and `notes`. See [GCAL.md](GCAL.md).

---

## equation

Renders LaTeX math to an image and prints it. Requires `pdflatex` and `pdftoppm`.

**Fields:** `latex`, `caption`, `size`

---

## Preview vs print

| Item | Preview | Print |
| ---- | ------- | ----- |
| Terminal borders (`\|===\|`) | Yes | No |
| `[CUT]` tear guide | Yes | No |
| Template content | Yes | Yes |
| Physical paper cut | No | Yes (unless `--no-cut`) |

---

## Creating your own template

1. Add `templates/mytemplate.j2` — Jinja2 layout using `{{ width }}` and your fields
2. Optionally add `templates/mytemplate.yaml` with name, description, and fields (shown by `printime list`)
3. Print with `--template mytemplate` or set `template: mytemplate` in markdown frontmatter

Available Jinja filters: `center`, `ljust`, `rjust`, `truncate` (all take width).
