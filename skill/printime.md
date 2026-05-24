---
name: printime
description: >-
  Operate the printime thermal printer CLI — print notes, checklists, QR codes,
  mermaid diagrams, Google Calendar agendas, Anytype pages, and web articles to
  ESC/POS receipt printers. Use when the user mentions printime, thermal printer,
  POS8370, receipt printing, print agenda, print QR, print note, Anytype print,
  diagram_flow, document template, or automating paper output from the command line.
---

# Printime

Thermal printer CLI for **ESC/POS receipt printers** (80mm, ~48 columns). Sends formatted text via **USB direct** — not CUPS Ctrl+P.

**Repo:** `~/Documents/repos/random_projects/printime`  
**Docs:** `docs/QUICKSTART.md`, `docs/COMMANDS.md`, `docs/TEMPLATES.md`, `docs/GCAL.md`, `docs/ANYTYPE.md`

## Before printing

1. `printime --version` (installed via `pipx`)
2. `printime doctor` — expect `idle`, USB found
3. `printime doctor --test-print` if unsure
4. Prefer **`--preview`** for user-facing jobs; **`--yes`** for cron/automation only
5. Never commit `.env`

## Install / update

```bash
pipx install -e ~/Documents/repos/random_projects/printime
pipx reinstall printime   # after code changes
```

Config: `config/printer.yaml` + `.env` in repo root.

## Command picker

| User wants | Command |
|------------|---------|
| Plain text | `printime print --text "..."` |
| Quick note | `printime print --template note --title "..." --content "..." --preview` |
| Markdown file | `printime print examples/note.md --preview` |
| Full page (headings + checklist + mermaid + QR) | `printime print examples/diagram_flow.md --preview` |
| Checklist | `printime print examples/checklist.md --preview` |
| Big centered QR | `printime print --qr "https://..."` |
| QR + URL below | `printime print --qr "https://..." --show-link` |
| Larger QR | `printime print --qr "URL" --qr-size 10` |
| WiFi slip | `printime print --qr 'WIFI:T:WPA;S:SSID;P:pass;;'` |
| Blog / article | `printime print --url 'https://...' --preview` |
| Image file | `printime print --image photo.png --preview` |
| Mermaid file | `printime print --mermaid flow.mmd --preview` |
| Today's calendar | `printime agenda --preview` |
| Next Mon–Sun week | `printime agenda --next-week --yes` |
| Anytype page by title | `printime anytype print "Page Title" --preview` |
| Search Anytype | `printime anytype search "query"` |
| List templates | `printime list` / `printime list document` |
| Webhook server | `printime serve --port 8080` |
| Help on typo | bad flags/commands print suggestions + subcommand `--help` |

## Templates

`note`, `checklist`, **document**, **diagram**, `task`, `jira`, `message`, `receipt`, `heading`, `agenda`, `equation`

**Auto-detection:** mixed body/checkboxes + mermaid or inline QR → `document`. Checkboxes only → `checklist`.

### Markdown inline blocks

````markdown
```mermaid
graph TD
  A --> B
```

```qr --qr-size 10 --center
"https://example.com"
```
````

Frontmatter: `title`, `caption`, `template`, plus template-specific fields. See `docs/TEMPLATES.md`.

## Anytype

Desktop API (port **31009**) — Anytype Desktop running, key in `.env`:

```bash
printime anytype print "Login Flow" --preview
```

- Page **name** = print title (unless YAML frontmatter `title:`)
- Add `caption:` via frontmatter pasted at top of page
- Normalizes escaped fences, tight checkboxes, plain mermaid blocks
- **Do not** use Ctrl+P in Anytype

## QR rules

- Default: large centered QR, no URL text below
- Long URLs (>300 chars): shorten first
- Inline QR in markdown: ` ```qr --qr-size N --center ` fence

## `.env` keys

```env
PRINTER_DEVICE=/dev/usb/lp5
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
GOOGLE_CALENDAR_ICS_URL=...
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=...
```

## Agent workflow

1. `printime doctor` if printer errors
2. `--preview` before printing unless user says print now
3. `--yes` for cron/automation only
4. Rich markdown / Anytype → expect `document` template
5. Mermaid needs `mermaid-cli` installed for physical diagram print

## Do not

- Use Ctrl+P / CUPS for template output
- Commit `.env`
- Assume markdown images render (QR and mermaid→PNG only)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `command not found` | `pipx install -e ~/Documents/repos/random_projects/printime` |
| Unknown flag | re-run; CLI suggests correct flag + `--help` |
| Anytype wrong template | `pipx reinstall printime` |
| Mermaid missing on paper | `npm i -g @mermaid-js/mermaid-cli` |
| CUPS `idle` | Normal — ready |

## More detail

- [docs/COMMANDS.md](../docs/COMMANDS.md)
- [docs/TEMPLATES.md](../docs/TEMPLATES.md)
- [docs/ANYTYPE.md](../docs/ANYTYPE.md)
- [docs/GCAL.md](../docs/GCAL.md)
- Cursor skill copy: [.cursor/skills/printime/SKILL.md](../.cursor/skills/printime/SKILL.md)
