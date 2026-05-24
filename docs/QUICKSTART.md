# Quick start

From zero to a printed note in under a minute.

## 1. Install (global CLI)

```bash
pipx install -e ~/Documents/repos/random_projects/printime[tickets]
```

If already installed without ticket support:

```bash
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
```

After code changes:

```bash
pipx reinstall printime
```

Copy config template and edit secrets locally:

```bash
cp ~/Documents/repos/random_projects/printime/.env.example \
   ~/Documents/repos/random_projects/printime/.env
```

## 2. Check the printer

```bash
printime doctor
printime doctor --test-print   # optional: prints a test page
```

`CUPS status: idle` is **good** — means ready, not broken.

If you get permission errors on `/dev/usb/lp5`:

```bash
sudo usermod -aG lp $USER
# log out and back in
```

## 3. Print plain text (simplest)

No template, no title bar — just text on paper:

```bash
printime print --text "Hello world"
printime print --text "URGENT" --bold --center
printime print --text "Right side" --center   # centered in 48 columns
```

Paper is cut automatically at the end (use `--no-cut` to skip).

## 4. Print a formatted note

### Option A — inline (fastest)

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm" \
  --preview
```

Print immediately:

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm"
```

### Option B — markdown file

```markdown
---
template: note
priority: high
---

# Quick note

Call dentist tomorrow at 3pm.
```

```bash
printime print notes/quick.md --preview
printime print examples/diagram_flow.md --preview   # full page with mermaid + QR
```

### Option C — big QR code

```bash
printime print --qr "https://calendar.google.com"
printime print --qr "https://..." --qr-size 10      # larger
printime print --qr "https://..." --show-link       # URL text below QR
```

WiFi guest slip:

```bash
printime print --qr 'WIFI:T:WPA;S:MyNetwork;P:password;;'
```

## 5. Google Calendar agenda

Add `GOOGLE_CALENDAR_ICS_URL` to `.env` (see [GCAL.md](GCAL.md)), then:

```bash
printime agenda --preview
printime agenda --next-week --yes
```

## 6. Anytype page

Desktop API in `.env` (see [ANYTYPE.md](ANYTYPE.md)), then:

```bash
printime anytype print "Login Flow" --preview
printime anytype search "Login"
```

Paste markdown into Anytype — printime normalizes escaped fences, checkboxes, and plain mermaid blocks. Add YAML frontmatter at the top for `caption`:

```yaml
---
title: Login Flow
caption: Happy path only
---
```

## 7. Preview only

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
```

`[CUT]` in preview is a tear guide — **not** printed on paper.

## Cheat sheet

| Goal | Command |
|------|---------|
| **Plain text** | `printime print --text "..."` |
| Bold / centered text | `printime print --text "..." --bold --center` |
| Formatted note | `printime print --template note --title "..." --content "..." --preview` |
| Note from file | `printime print my-note.md --preview` |
| Full page (mermaid + QR) | `printime print examples/diagram_flow.md --preview` |
| QR code | `printime print --qr "https://..."` |
| Blog / URL | `printime print --url 'https://...' --preview` |
| Calendar today | `printime agenda --preview` |
| Calendar next week | `printime agenda --next-week --yes` |
| Anytype page | `printime anytype print "Page title" --preview` |
| CLI help on typos | mistyped flags show `--help` for that command |
| Skip confirmation | add `--yes` |
| No paper cut | add `--no-cut` |
| List templates | `printime list` |

## Next steps

- [COMMANDS.md](COMMANDS.md) — full CLI reference
- [TEMPLATES.md](TEMPLATES.md) — templates and frontmatter
- [CONFIG.md](CONFIG.md) — printer configuration
- [GCAL.md](GCAL.md) — Google Calendar setup
- [ANYTYPE.md](ANYTYPE.md) — Anytype integration
