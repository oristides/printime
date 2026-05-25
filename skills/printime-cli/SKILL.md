---
name: printime
description: >-
  Operate the printime thermal printer CLI — print notes, checklists, QR codes,
  mermaid diagrams, ticket PDFs, Google Calendar, Anytype pages, and web articles and blogs, 
  on ESC/POS thermal printers. Use for printime, thermal printer, receipt print,
  agenda, QR, Anytype, ticket PDF, or automating paper output.
---

# Printime

Thermal printer CLI for **ESC/POS receipt printers** (typically 80mm, ~48 columns). USB direct — not CUPS Ctrl+P.

**Repo:** `~/Documents/repos/random_projects/printime`  
**Docs:** `docs/QUICKSTART.md`, `docs/COMMANDS.md`, `docs/CONFIG.md`, `docs/TEMPLATES.md`

## Install / reinstall (pipx)

```bash
# First time (with ticket PDF support):
pipx install -e ~/Documents/repos/random_projects/printime[tickets]

# After git pull / code changes:
pipx install -e ~/Documents/repos/random_projects/printime[tickets] --force

# Add ticket deps to existing pipx install:
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
```

Do **not** use system `pip install` (PEP 668). Always **pipx**.

Configure printer: copy `config/printer.example.yaml` → `config/printer.yaml`, edit for **your** device/USB IDs. See `docs/CONFIG.md`.

## Agent workflow — always read preview

1. `printime doctor` if first run or errors  
2. **`--preview`** before printing (unless user says print now)  
3. **Self-read the preview** — do not trust code alone:

```python
from printime.preview_capture import render_and_summarize, read_preview, capture_cli_preview

# From context:
result = render_and_summarize('ticket', context, config)
print(read_preview(result['preview']))  # digest
print(result['preview'])                # full paper simulation

# From CLI:
cap = capture_cli_preview(['print', '--ticket', 'ticket.pdf', '--preview', '--yes'])
print(read_preview(cap['preview']))
```

4. Check: title block, **QR size** (~matches `--qr-size`), Unicode (São Paulo, ã), segment order, `[CUT]`  
5. `--yes` only for cron / user-confirmed print

## Command picker

| User wants | Command |
|------------|---------|
| Plain text | `printime print --text "..."` |
| Markdown inline | `printime print --markdown --text "# Title\nBody" --preview` |
| Markdown file | `printime print notes.md --preview` |
| Full page + QR | `printime print examples/diagram_flow.md --preview` |
| Blog + link QR | `printime print --url 'https://...' --link-qr --preview` |
| Ticket PDF | `printime print --ticket ticket.pdf --preview` |
| Big QR | `printime print --qr "https://..." --qr-size 10` |
| Anytype page | `printime anytype print "Title" --preview` |
| Calendar week | `printime agenda --next-week --preview` |
| List templates | `printime list` / `printime --help` |

## Templates

`note`, `checklist`, `document`, `diagram`, `ticket`, `task`, `jira`, `message`, `receipt`, `heading`, `agenda`, `equation`

Markdown: `#`/`##`/`###`, `**bold**`, `- [ ]`, ` ```qr ` / ` ```mermaid ` fences.

## Encoding

- Preview: Unicode OK (`São Paulo`)  
- Print: `encoding: cp850` in `config/printer.yaml` (Western Europe)  
- If garbled on paper → try `latin-1` or `ascii`

## QR preview vs print

Preview ASCII QR scales with **`--qr-size`** and **`paper_width_pixels`** to match printed proportion. Verify visually in preview before `--yes`.

## `.env` (secrets — never commit)

```env
PRINTER_DEVICE=/dev/usb/lp0
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
GOOGLE_CALENDAR_ICS_URL=...
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=...
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Ticket PDF pymupdf error | `pipx inject printime pymupdf ...` |
| Wrong printer device | Edit `config/printer.yaml` from `printer.example.yaml` |
| `ã` → `?` on paper | Set `encoding: cp850` |
| Preview QR too small vs print | Update printime; QR preview now scales with `--qr-size` |
| Mermaid on paper | `npm i -g @mermaid-js/mermaid-cli` |

## More detail

- [docs/CONFIG.md](../docs/CONFIG.md) — printer setup (agnostic)
- [docs/COMMANDS.md](../docs/COMMANDS.md)
- [docs/TEMPLATES.md](../docs/TEMPLATES.md)
