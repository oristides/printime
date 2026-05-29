---
name: printime-cli
description: >-
  Use when operating the Printime CLI, ESC/POS thermal printers, notes, task, checklist and other
  printing options like markdown notes, QR codes, ticket PDFs,
  Anytype/Notion/Markdown pages,  email summaries templates, or automation via printime serve.
metadata:
  repository: ~/Documents/repos/random_projects/printime
  package: printime
  primaryConfig: config/printer.yaml
  primaryEnv: .env
inputs:
  - name: PRINTER_DEVICE
    required: true
    description: Direct USB device such as /dev/usb/lp0 or /dev/usb/lp5.
  - name: PRINTER_BACKEND
    required: false
    description: Printer backend; usb is the recommended default.
  - name: ANYTYPE_API_KEY
    required: false
    description: Anytype Desktop API key for printing pages by title.
  - name: GOOGLE_CALENDAR_ICS_URL
    required: false
    description: Private Google Calendar ICS URL for agenda printing.
  - name: GOOGLE_KEEP_MASTER_TOKEN
    required: false
    description: Google Keep gkeepapi master token; treat as a password.
references:
  - references/install.md
  - references/agent-protocol.md
  - references/commands.md
  - references/printing.md
  - references/templates.md
  - references/integrations.md
  - references/troubleshooting.md
---

# Printime CLI

Printime is a CLI-first thermal printer tool for **ESC/POS receipt printers** (80mm, 48 columns).

---

## 1 · Before You Print Anything

Run these checks once per session (or after any printer failure):

```bash
# Is printime installed and healthy?
(command -v printime >/dev/null && printime --version) || \
  pipx install -e ~/Documents/repos/random_projects/printime[all] --force
printime doctor
```

`CUPS status: idle` is normal (means ready). If `doctor` reports a device or
permission error, fix it before continuing → [references/troubleshooting.md](references/troubleshooting.md).

---

## 2 · The Preview / Print Contract

**This is the most important rule.** Understand it before issuing any command.

| Command form | What happens |
|---|---|
| `printime print FILE --preview` | Terminal preview only. **No paper.** |
| `printime print FILE --preview --yes` | Preview, then print. |
| `printime print FILE --yes` | Print immediately, no preview. |
| `printime print FILE` | Print immediately, no preview. |

**Default for agents: always add `--preview` first. Read the output. Add `--yes` only after:**
- The user explicitly approved the preview, OR
- The user asked for immediate physical output, OR
- The job is trusted cron / automation.

`[CUT]` in preview output is a marker — it is not printed as text.

---

## 3 · Choose the Right Command (Decision Tree)

```
What does the user want to print?
│
├─ Personal note / quick memo          →  --template note
├─ Checkbox / todo list                →  --template checklist --title "…" --items "A|B::x|C"
├─ Short alert / message slip          →  --template message
├─ Email summary                       →  --template email  (or examples/email.md)
├─ Markdown file (.md)                 →  printime print FILE.md
├─ Enriched markdown inline            →  --markdown --text $'# ...'
├─ Google Calendar agenda              →  printime agenda --today | --days N | --next-week
├─ Anytype page                        →  printime anytype print "Title"
├─ Google Keep note                    →  printime keep print "URL or ID"
├─ Web article / URL                   →  --url 'https://...'
├─ Ticket PDF                          →  printime print ticket.pdf
├─ ASCII art banner                    →  --ascii "text" --ascii-font slant --center
├─ QR code (standalone)                →  --qr "https://..." --qr-size 10
├─ Image                               →  --image photo.png
├─ Mermaid diagram                     →  --mermaid flow.mmd
├─ HTTP automation                     →  printime serve --port 8080
└─ Raw text (no template, last resort) →  --text "..."
```

---

## 4 · Template Auto-Detection

When printing a `.md` file without `--template`, Printime picks the template automatically:

| Content in the file | Chosen template |
|---|---|
| Headings + mermaid or inline QR blocks | `document` |
| Mermaid only | `diagram` |
| Checkboxes only | `checklist` |
| Plain prose | `note` |
| Positional `.pdf` file | `ticket` |

To force a specific template: `--template <name>` or set `template:` in YAML frontmatter.

Run `printime list` to list all templates. Run `printime list <name>` to see its fields.

---

## 5 · Quick Command Reference

```bash
# Notes and messages
printime print --template note --title "Today" --content "Ship docs" --preview
printime print --template checklist --title "Market" --items "Milk|Bread::x|Eggs" --preview
printime print --template message --title "Alert" --content "Printer ready" --preview

# Email
printime print examples/email.md --preview
printime print --template email --file examples/email.json --preview
printime list email                          # show all email fields

# Markdown
printime print notes.md --preview
printime print --markdown --text $'# Title\n\n- [ ] Task' --preview

# Calendar / integrations
printime agenda --today --preview
printime agenda --days 7 --preview
printime agenda --next-week --preview
printime anytype print "Login Flow" --preview
printime keep print "https://keep.google.com/#NOTE/..." --preview

# Media
printime print ticket.pdf --preview
printime print --url "https://example.com/article" --preview
printime print --qr "https://example.com" --qr-size 10 --show-link --preview
printime print --ascii "hello" --ascii-font slant --center --preview

# Info / diagnostics
printime list
printime ascii-fonts
printime doctor --test-print

# Automation
printime serve --port 8080
```

---

## 6 · Guard-Rails (Common Mistakes to Avoid)

| ❌ Wrong | ✅ Right |
|---|---|
| `--text` for notes / checklists / messages | Use `--template note`, `--template checklist --items "…"`, or `--template message` |
| Ctrl+P to POS8370 for articles, Anytype, PDFs | Use `printime print` or `printime serve` |
| `--yes` without reading preview | Run `--preview` first; only add `--yes` after approval |
| `pip install` in system Python | Use `pipx install -e ...` or `pipx inject printime ...` |
| `printime print --url <keep-url>` | Keep URLs use fragments; use `printime keep print` instead |
| Long URL → huge dense QR code | Shorten URLs above ~300 chars before generating QR |
| Mermaid missing on paper | `npm install -g @mermaid-js/mermaid-cli` |
| Garbled Portuguese accents on paper | Set `encoding: cp860` in `config/printer.yaml` |

---

## 7 · Key Notes Per Content Type

**`checklist`** — `--items "A|B::x|C"` (pipe-separated). Checked: append `::x` or `::checked`. Colons in labels OK (`Deploy: staging`). Optional `--content` for prose. Auto datetime under title.

**`note`, `message`, `agenda`** — auto `YYYY-MM-DD HH:MM` under title. Override with `date:` only when needed.

**`email`** — fields: `subject`, `sender` (YAML `from:` maps here), `to`, `cc`, `reply_to`, `date`, `body`, `labels`, `message_id`. `to` and `cc` accept a string or list.

**Tables in markdown** — target 3–4 columns for 48-column paper. 5 columns is the practical max. More than 5 columns renders but becomes unreadable.

**ASCII art fonts** — public choices are limited to: `pagga`, `avatar`, `bulbhead`, `banner`, `slant`. Others are internal fallbacks only. Run `printime ascii-fonts` to confirm.

**Article URLs** — works best on readable article pages. Paywalls and heavy JS may fail. Use `--max-chars 3000` to limit length, or `--max-chars 0` for no limit.

**`printime serve`** — no auth. Use only on localhost, LAN, or Tailscale.

---

## 8 · When to Load References

Load one reference only when you need it. Each file opens with what it contains — confirm you picked the right one.

| Situation | File | Contains |
|---|---|---|
| Install, update, extras, printer config | [install.md](references/install.md) | pipx install, **extra → feature** table, `printer.yaml` / `.env` fields |
| Programmatic preview in Python | [agent-protocol.md](references/agent-protocol.md) | `capture_cli_preview`, `render_and_summarize`, preview inspection checklist |
| Exact flag name or HTTP JSON body | [commands.md](references/commands.md) | Full flag tables per subcommand, `serve` payloads (no examples) |
| Non-obvious print details | [printing.md](references/printing.md) | Checklist `--items` syntax, ticket `.pdf` vs `--ticket`, image width, plain `--text` caveat |
| Template fields, tables, fences | [templates.md](references/templates.md) | Per-template fields, frontmatter, QR/mermaid fences, **table column limits** |
| Anytype / Calendar / Keep / HTTP | [integrations.md](references/integrations.md) | Env vars, Desktop vs Bot API, integration commands |
| Errors, encoding, USB, CUPS | [troubleshooting.md](references/troubleshooting.md) | Problem/fix table, **cp860 for Portuguese**, USB + secrets note |
