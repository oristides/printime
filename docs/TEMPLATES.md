# Templates

Printime renders **Jinja2 templates** (`.j2` files in `templates/`) using data from markdown frontmatter, inline CLI flags, or JSON/YAML files.

List available templates:

```bash
printime list
```

## Markdown-first workflow

Write a `.md` file with optional YAML frontmatter:

```markdown
---
template: note
title: My Title
priority: high
tags: [work]
---

# My Title

Body text here. Supports **bold**, lists, and paragraphs.
```

Print:

```bash
printime print my-file.md --preview
```

### Frontmatter rules

- `template` — which template to use (defaults to `note`)
- Any other key maps directly to template variables (`title`, `priority`, `tags`, etc.)
- A `# Heading` at the top of the body becomes `title` if not set in frontmatter
- `- [ ]` / `- [x]` lines auto-select the `checklist` template

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

**Output layout:**

```
================================================
                  QUICK NOTE
================================================
[HIGH]

Remember to send the report

------------------------------------------------
Tags: work
```

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

## jira

Compact Jira ticket printout.

**Fields:** `ticket_id`, `summary`, `description`, `status`, `priority`, `assignee`, `labels`

Note: use `summary` in frontmatter, or set `title` / `# Heading` — it maps to `summary` automatically.

**Markdown example** (`examples/jira.md`):

```markdown
---
template: jira
ticket_id: PROJ-123
status: In Progress
priority: high
assignee: Oriel
labels: [printime, bug]
---

# Align print output with preview

The physical print should match the preview layout.
```

## message

Short message with title and body (simpler than `note` — no priority/tags).

**Fields:** `title`, `content`

```bash
printime print --template message \
  --title "Reminder" \
  --content "Team lunch at 12pm" \
  --preview
```

## heading

Large heading text for labels or section markers.

**Fields:** `text`, `style`

## receipt

Receipt-style layout with line items and totals.

**Fields:** `store_name`, `date`, `items`, `subtotal`, `tax`, `total`, `payment_method`

## equation

Renders LaTeX math to an image and prints it. Requires `pdflatex` and `pdftoppm`.

**Fields:** `latex`, `caption`, `size`

See `examples/equation_einstein.md` and related latex examples.

## Preview vs print

| | Preview | Print |
|---|---------|-------|
| Terminal borders (`\|===\|`) | Yes | No |
| `[CUT]` tear guide | Yes | No |
| Template content | Yes | Yes |
| Physical paper cut | No | Yes (unless `--no-cut`) |

## Creating your own template

1. Add `templates/mytemplate.j2` — Jinja2 layout using `{{ width }}` and your fields
2. Optionally add `templates/mytemplate.yaml` with name, description, and fields (shown by `printime list`)
3. Print with `--template mytemplate` or set `template: mytemplate` in markdown frontmatter

Available Jinja filters: `center`, `ljust`, `rjust`, `truncate` (all take width).
