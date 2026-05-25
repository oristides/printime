---
name: printime-cli
description: >-
  Operate the printime thermal printer CLI — print notes, checklists, QR codes,
  mermaid diagrams, ticket PDFs, Google Calendar, Anytype pages, and web articles and blogs, 
  on ESC/POS thermal printers. Use for printime, thermal printer, receipt print,
  agenda, QR, Anytype, ticket PDF, or automating paper output.
---

# Printime

Thermal printer CLI for **ESC/POS receipt printers** (typically 80mm, ~48 columns). **CLI-first** — for users, agents, and apps (`printime serve`). Not CUPS Ctrl+P.

**Repo:** `~/Documents/repos/random_projects/printime`  
**Docs:** `docs/QUICKSTART.md`, `docs/COMMANDS.md`, `docs/HOTKEYS.md`, `docs/CONFIG.md`, `docs/TEMPLATES.md`

## Install / reinstall (pipx)

```bash
pipx install -e ~/Documents/repos/random_projects/printime[tickets] --force
```

Do **not** use system `pip install` (PEP 668). Always **pipx**.

Configure printer: copy `config/printer.example.yaml` → `config/printer.yaml`. See `docs/CONFIG.md`.

## Agent workflow — always read preview

1. `printime doctor` if first run or errors  
2. **`--preview`** before printing (unless user says print now)  
3. **Self-read the preview** — do not trust code alone:

```python
from printime.preview_capture import render_and_summarize, read_preview, capture_cli_preview

cap = capture_cli_preview(['print', '--ticket', 'ticket.pdf', '--preview', '--yes'])
print(read_preview(cap['preview']))
```

4. Check: title block, QR size, Unicode, segment order, `[CUT]`  
5. `--yes` only for cron / user-confirmed print

## Command picker

| User wants | Command |
|------------|---------|
| Plain text | `printime print --text "..."` |
| Markdown file | `printime print notes.md --preview` |
| Blog + link QR | `printime print --url 'https://...' --link-qr --preview` |
| Ticket PDF | `printime print --ticket ticket.pdf --preview` |
| Anytype page | `printime anytype print "Title" --preview` |
| Keep note | `printime keep print "<url>" --preview` |
| Calendar week | `printime agenda --next-week --preview` |
| HTTP automation | `printime serve --port 8080` |
| Desktop hotkey | `scripts/anytype-print.sh`, `scripts/print-url.sh` — see `docs/HOTKEYS.md` |

## Hotkeys (users)

```bash
scripts/anytype-print.sh "Page title"   # --preview; PRINTIME_YES=1 for instant print
scripts/print-url.sh                    # URL from clipboard
scripts/print-ticket.sh                 # PDF path from clipboard
```

Do **not** use Ctrl+P → POS8370. See `docs/HOTKEYS.md`.

## Templates

`note`, `checklist`, `document`, `diagram`, `ticket`, `task`, `jira`, `message`, `receipt`, `heading`, `agenda`, `equation`

## `.env` (secrets — never commit)

```env
PRINTER_DEVICE=/dev/usb/lp0
ANYTYPE_API_KEY=...
GOOGLE_CALENDAR_ICS_URL=...
```

## More detail

- [docs/HOTKEYS.md](../docs/HOTKEYS.md) — shortcuts and integrations
- [docs/COMMANDS.md](../docs/COMMANDS.md)
- [docs/TEMPLATES.md](../docs/TEMPLATES.md)
