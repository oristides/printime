# Quick start

This guide gets you from zero to a printed note in under a minute.

## 1. Install

```bash
cd ~/Documents/repos/random_projects/adhd/printime
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional — add to your shell profile so `printime` is always available:

```bash
export PATH="$HOME/Documents/repos/random_projects/adhd/printime/.venv/bin:$PATH"
```

## 2. Check the printer

```bash
printime doctor
printime doctor --test-print   # optional: prints a test page
```

If you get permission errors on `/dev/usb/lp5`, add yourself to the `lp` group and log in again.

## 3. Print a quick note

There are three ways, from fastest to most reusable.

### Option A — inline (fastest, no file)

Use the `note` template directly from the command line:

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm" \
  --preview
```

Preview shows what the paper will look like and asks `Print this? [Y/n]`.

Print immediately without preview:

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm"
```

Optional fields:

```bash
printime print --template note \
  --title "Standup" \
  --content "Discuss blockers and sprint goals" \
  --priority high \
  --tags "work,team" \
  --preview
```

### Option B — markdown file (best for notes you reuse or edit)

Create a file, e.g. `notes/quick.md`:

```markdown
---
template: note
priority: high
tags: [errands]
---

# Quick note

Call dentist tomorrow at 3pm.
Pick up dry cleaning on the way back.
```

Print it:

```bash
printime print notes/quick.md --preview
```

You can omit `template: note` in frontmatter — markdown files default to the note template unless they contain checkboxes (which auto-select checklist).

Minimal version (no frontmatter):

```markdown
# Quick note

Call dentist tomorrow at 3pm.
```

```bash
printime print notes/quick.md --preview
```

### Option C — plain text (no template formatting)

For a single line with no title bar or borders:

```bash
printime print --text "Call dentist tomorrow at 3pm"
```

This skips the `note` template entirely and prints raw text.

## 4. Preview only (no print)

To see the layout without sending anything to the printer:

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
```

The `[CUT]` line in preview is a tear guide for you — it is **not** printed on paper.

## 5. Checklists

Use markdown checkboxes:

```markdown
---
title: Shopping
---

- [ ] Milk
- [x] Bread
- [ ] Eggs
```

```bash
printime print shopping.md --preview
```

Checkboxes automatically use the `checklist` template. See [TEMPLATES.md](TEMPLATES.md) for details.

## Cheat sheet

| Goal | Command |
|------|---------|
| Quick note, inline | `printime print --template note --title "..." --content "..." --preview` |
| Quick note, from file | `printime print my-note.md --preview` |
| Plain text only | `printime print --text "..."` |
| Preview only | `printime preview --file my-note.md` |
| Skip confirmation | add `--yes` |
| No paper cut | add `--no-cut` |
| List templates | `printime list` |

## Next steps

- [TEMPLATES.md](TEMPLATES.md) — all templates and frontmatter fields
- [COMMANDS.md](COMMANDS.md) — full CLI reference
- [CONFIG.md](CONFIG.md) — printer configuration and troubleshooting
- [ANYTYPE.md](ANYTYPE.md) — print Anytype pages
