# Printime

Thermal printer CLI with markdown-first templates, terminal preview, and integrations.

**Repo:** [github.com/oristides/printime](https://github.com/oristides/printime)

## Quick start

```bash
pipx install -e ~/Documents/repos/random_projects/printime
cp ~/Documents/repos/random_projects/printime/.env.example ~/Documents/repos/random_projects/printime/.env
printime doctor
```

**Print plain text:**

```bash
printime print --text "Hello world"
```

**Print a formatted note (preview first):**

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm" \
  --preview
```

See **[docs/QUICKSTART.md](docs/QUICKSTART.md)** for the full guide.

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Install, plain text, notes, checklists |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Full CLI reference |
| [docs/TEMPLATES.md](docs/TEMPLATES.md) | Every template and markdown examples |
| [docs/CONFIG.md](docs/CONFIG.md) | Printer setup, USB/CUPS, troubleshooting |
| [docs/GCAL.md](docs/GCAL.md) | Google Calendar agenda |
| [docs/ANYTYPE.md](docs/ANYTYPE.md) | Print Anytype pages |
| [docs/NATIVE.md](docs/NATIVE.md) | Hotkeys, Ctrl+P vs printime |
| [skill/printime.md](skill/printime.md) | Agent skill for Cursor / automation |

## Common commands

```bash
printime print --text "Hello"                        # plain text
printime print --qr "https://example.com"            # big centered QR
printime print examples/diagram_flow.md --preview    # full page: headings, checklist, mermaid, QR
printime print examples/note.md --preview            # simple note
printime agenda --next-week --preview                # Google Calendar week
printime anytype print "Page title" --preview        # Anytype page (auto document layout)
printime print --url 'https://...' --preview         # blog / article
printime doctor --test-print                         # test page
printime print --help                                # flags + examples on typos
```

## Preview vs print

- **Preview** shows a terminal simulation with paper borders and a `[CUT]` tear guide.
- **Print** sends only the template text to the printer. `[CUT]` is never printed; the printer cuts at the end.

## Examples

Markdown examples in `examples/`: `note.md`, `checklist.md`, `task.md`, `jira.md`, `diagram_flow.md` (headings + checklist + mermaid + inline QR)

## License

MIT
