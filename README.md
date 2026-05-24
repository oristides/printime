# Printime

Thermal printer CLI with markdown-first templates, terminal preview, and integrations.

## Quick start

```bash
cd ~/Documents/repos/random_projects/adhd/printime
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
printime doctor
```

**Print a quick note (preview first, recommended):**

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm" \
  --preview
```

**Print a note from a markdown file:**

```bash
printime print notes/quick.md --preview
```

See **[docs/QUICKSTART.md](docs/QUICKSTART.md)** for the full quick-note guide.

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Install, first print, quick notes, checklists |
| [docs/TEMPLATES.md](docs/TEMPLATES.md) | Every template, fields, markdown examples |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Full CLI reference |
| [docs/CONFIG.md](docs/CONFIG.md) | Printer setup, USB/CUPS, troubleshooting |
| [docs/ANYTYPE.md](docs/ANYTYPE.md) | Print pages from Anytype |
| [docs/GCAL.md](docs/GCAL.md) | Print today's Google Calendar agenda |
| [docs/NATIVE.md](docs/NATIVE.md) | System install, hotkeys, Ctrl+P vs printime |

## Common commands

```bash
printime list                              # list templates
printime preview --file examples/note.md   # preview without printing
printime print examples/checklist.md -p    # checklist from markdown
printime doctor --test-print               # send a test page
printime agenda --preview                  # today's Google Calendar
```

## Preview vs print

- **Preview** shows a terminal simulation with paper borders and a `[CUT]` tear guide.
- **Print** sends only the template text to the printer. `[CUT]` is never printed; the printer performs a physical cut at the end.

## Examples

Markdown examples live in `examples/`:

- `note.md` — quick personal note
- `checklist.md` — shopping list with checkboxes
- `task.md` — single task with due date
- `jira.md` — ticket summary
- `oriel-mandates.md` — longer note with bullets

## License

MIT
