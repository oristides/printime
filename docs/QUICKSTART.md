# Quick start

From zero to a printed note in under a minute.

## 1. Install (global CLI)

```bash
(command -v printime >/dev/null && printime --version) || pipx install -e ~/Documents/repos/random_projects/printime[all] --force; printime doctor
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

## 3. Print a formatted note

Prefer templates over raw text. `note`, `checklist`, `message`, and `agenda` add an automatic `YYYY-MM-DD HH:MM` line under the title/subtitle.

```bash
printime print --template note \
  --title "Quick note" \
  --content "Call dentist tomorrow at 3pm" \
  --preview
```

## 4. More ways to print

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
printime agenda --today --preview
printime agenda --days 7 --preview
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

`--preview` and `printime preview` render terminal output only. They do not
print paper unless you also pass `--yes`; `[CUT]` is a tear guide, **not**
printed text.

## Cheat sheet

| Goal | Command |
|------|---------|
| Formatted note | `printime print --template note --title "..." --content "..." --preview` |
| Message | `printime print --template message --title "..." --content "..." --preview` |
| Email summary | `printime print examples/email.md --preview` |
| Note from file | `printime print my-note.md --preview` |
| Full page (mermaid + QR) | `printime print examples/diagram_flow.md --preview` |
| QR code | `printime print --qr "https://..."` |
| Blog / URL | `printime print --url 'https://...' --preview` (link QRs on by default) |
| Calendar today | `printime agenda --today --preview` |
| Calendar this week | `printime agenda --days 7 --preview` |
| Calendar next week | `printime agenda --next-week --yes` |
| Anytype page | `printime anytype print "Page title" --preview` |
| Plain text fallback | `printime print --text "..."` |
| CLI help on typos | mistyped flags show `--help` for that command |
| Print after preview | add `--yes` |
| No paper cut | add `--no-cut` |
| List templates | `printime list` |

## Next steps

- [COMMANDS.md](COMMANDS.md) — full CLI reference
- [TEMPLATES.md](TEMPLATES.md) — templates and frontmatter
- [CONFIG.md](CONFIG.md) — printer configuration
- [HOTKEYS.md](HOTKEYS.md) — shortcuts for Anytype, URLs, tickets
- [GCAL.md](GCAL.md) — Google Calendar setup
- [ANYTYPE.md](ANYTYPE.md) — Anytype integration
