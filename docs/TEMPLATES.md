# Templates

Printime renders **Jinja2 templates** (`.j2` files in `templates/`) using data from markdown frontmatter, inline CLI flags, or JSON/YAML files.

List available templates:

```bash
printime list
printime list document    # fields for one template
```

## Markdown-first workflow

Write a `.md` file with optional YAML frontmatter:

```markdown
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
```

Print:

```bash
printime print my-file.md --preview
printime print examples/diagram_flow.md --preview
```

See `examples/diagram_flow.md` for a full mixed-content page.

### Frontmatter fields

| Field | Purpose |
|-------|---------|
| `template` | Force a template (`note`, `document`, `checklist`, …). Auto-detected if omitted. |
| `title` | Header title (between `====` lines). Falls back to `# Heading` or filename. |
| `caption` | Subtitle under title in the header block (not a diagram label). |
| Other keys | Map to template variables (`priority`, `tags`, `due_date`, …). |

### Auto template detection

| Content | Template |
|---------|----------|
| Mermaid and/or inline QR **plus** body text or checkboxes | `document` |
| Mermaid only | `diagram` |
| Checkboxes only | `checklist` |
| Plain prose | `note` |

### Markdown body syntax

- `#` / `##` / `###` — heading sizes (left-aligned; use `<center>...</center>` to center)
- `- [ ]` / `- [x]` — checklist items (one line per item on paper)
- ` ```mermaid ` … ` ``` ` — diagram (rendered via mermaid-cli if installed)
- Plain ` ``` ` fence with `graph TD` / `flowchart` — also treated as mermaid (Anytype export)
- ` ```qr [flags] ` … ` ``` ` — inline QR block

**QR fence flags** (same as CLI):

```markdown
```qr --qr-size 10 --center --show-link
"https://example.com"
```
```

- `--qr-size` — module size 4–12 (default 8)
- `--center` — center on paper
- `--show-link` — print URL text below QR

### Title header layout

When `title` (and optional `caption`) are set, they print together at the top:

```
================================================
LOGIN FLOW
Happy path only
================================================
```

Body headings (`#`, `##`) print below this block — they do not replace the frontmatter title.

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

Personal note with title, body, optional priority and tags.

**Fields:** `title`, `content`, `priority`, `tags`

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

Checkbox list for shopping lists, todos, etc.

**Fields:** `title`, `items` (each item: `text`, `checked`)

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

Short message with title and body (simpler than `note` — no priority/tags).

**Fields:** `title`, `content`

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

Calendar day/week layout with times, event titles, and locations.

**Fields:** `title`, `days`, `empty_message`, `source`

Used automatically by `printime agenda`. See [GCAL.md](GCAL.md).

---

## equation

Renders LaTeX math to an image and prints it. Requires `pdflatex` and `pdftoppm`.

**Fields:** `latex`, `caption`, `size`

---

## Preview vs print

| | Preview | Print |
|---|---------|-------|
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
