---
name: printime-cli
description: >-
  Use when operating the printime CLI, ESC/POS thermal printers, receipt
  printing, POS8370, print previews, markdown notes, QR codes, ticket PDFs,
  Anytype pages, Google Calendar agendas, Google Keep notes, templates, or
  automation via printime serve.
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

Printime is a CLI-first thermal printer tool for **ESC/POS receipt printers** (usually 80mm, 48 columns). Agents should use `printime` commands, templates, previews, or `printime serve`; do not use Ctrl+P to the raw CUPS queue for templated output.

## Installation

Check or install the full Python extras in one line:

```bash
(command -v printime >/dev/null && printime --version) || pipx install -e ~/Documents/repos/random_projects/printime[all] --force; printime doctor
```

Do not use system `pip install` on this machine; use `pipx`. For setup, extras, printer config, and update commands, read [references/install.md](references/install.md).

Prefer templates over raw text. Templates provide title blocks, automatic minute-precision datetime, structured fields, and consistent receipt layout.

## Agent Protocol

The CLI is paper-producing software. Agents should treat physical printing as a side effect.

- Use `--template note`, markdown files, or integration-specific templates before falling back to pure `--text`.
- Use `--preview` to inspect output only. It does not print paper by itself.
- Read the preview output; check title blocks, QR size, Unicode, section order, and `[CUT]`.
- Use `--yes` only after preview approval, explicit user confirmation, cron,
  or other unattended automation. With `--preview --yes`, printime previews
  first and then prints.
- Omit `--preview` only when the user explicitly wants immediate physical printing.
- Never commit `.env`; it may contain Anytype keys, Google Calendar ICS URLs, and Google Keep master tokens.
- Run `printime doctor` before troubleshooting printer or USB failures.

Detailed preview capture workflow: [references/agent-protocol.md](references/agent-protocol.md).

## Command picker

| User wants | Command |
| ------------ | ------- |
| Quick note | `printime print --template note --title "Today" --content "Ship docs" --preview` |
| Checklist | `printime print --template checklist --file checklist.yaml --preview` |
| Short message | `printime print --template message --title "Alert" --content "Printer is ready" --preview` |
| Markdown file | `printime print notes.md --preview` |
| Markdown table | `printime print examples/oriel-mandates.md --preview` |
| Enriched text | `printime print --markdown --text "# Title\n\n- [ ] Task" --preview` |
| Today's Google Calendar agenda | `printime agenda --today --preview` |
| This week from today | `printime agenda --days 7 --preview` |
| Next Mon-Sun week | `printime agenda --next-week --preview` |
| Blog / article URL | `printime print --url 'https://...' --preview` |
| Ticket PDF | `printime print ticket.pdf --preview` |
| Anytype page | `printime anytype print "Title" --preview` |
| Google Keep note | `printime keep print "https://keep.google.com/#NOTE/..." --preview` |
| HTTP automation | `printime serve --port 8080` |
| Diagnose printer | `printime doctor --test-print` |
| Big QR code | `printime print --qr "https://..." --qr-size 10` |
| Plain text fallback | `printime print --text "..."` |

## Available Commands

| Command | What it does |
| ------- | ------------ |
| `print` | Print text, markdown, QR codes, URLs, images, mermaid diagrams, templates, and ticket PDFs. |
| `preview` | Render a terminal preview from text, a template, or a context file. |
| `list` | List templates or show fields for one template. |
| `transform` | Convert markdown, text, LaTeX, or URL content to context/image output. |
| `doctor` | Diagnose printer config, USB device, CUPS queue, and optional test print. |
| `serve` | Start a local HTTP print endpoint for app or agent automation. |
| `agenda` | Print Google Calendar agendas from a private ICS URL. |
| `anytype` | Search, fetch, and print Anytype Desktop pages. |
| `keep` | Search, list, and print Google Keep notes via `gkeepapi`. |

Full command details: [references/commands.md](references/commands.md).

## Common Patterns

**Template note first:**

```bash
printime print --template note --title "Today" --content "Ship docs" --preview
```

`note`, `checklist`, `message`, and `agenda` automatically print `YYYY-MM-DD HH:MM` below the title/subtitle. Override with a `date` field only when the paper should show a specific time.

**Preview then print:**

```bash
printime print notes.md --preview
printime print notes.md --yes
```

`--preview` is the safe default for agents: it renders the terminal receipt
and stops. No physical paper is printed unless the command also includes
`--yes`, or unless you run the print command without `--preview`.

**Tables and enriched markdown:**

```bash
printime print examples/oriel-mandates.md --preview
printime print --markdown --text $'# Today\n\n**Top risks**\n\n| Metric | Owner | Status | Next |\n| --- | --- | --- | --- |\n| Activation | Ana | Green | Watch signups |' --preview
printime anytype print "rETROSUM" --preview
```

Markdown tables are rendered as receipt-friendly columns; Anytype `<br>` table markup is normalized. On 48-character paper, prefer 2-3 columns for readability, 4 columns for compact dashboards, and 5 columns only for dense summaries.

**Google Calendar agenda:**

```bash
printime agenda --today --preview
printime agenda --days 7 --preview
printime agenda --next-week --preview
```

**Print an article with source QR segments:**

```bash
printime print --url "https://example.com/article" --preview
```

**Print a ticket PDF:**

```bash
printime print ~/Downloads/ticket.pdf --preview
```

**Print an Anytype page:**

```bash
printime anytype print "Login Flow" --preview
```

**Automation endpoint:**

```bash
printime serve --port 8080
```

## Common Mistakes

| Mistake | Fix |
| ------- | --- |
| Using raw `--text` for notes/checklists/messages | Use `--template note`, `--template checklist`, or `--template message`. |
| Using Ctrl+P to POS8370 for articles, Anytype, or tickets | Use `printime print` or `printime serve`. |
| Printing physically without checking layout | Add `--preview`, then read the preview before adding `--yes`. |
| Using `pip install` in system Python | Use `pipx install -e ...` or `pipx inject printime ...`. |
| Expecting Keep URLs to work with `--url` | Use `printime keep print`, because Keep note IDs live in URL fragments. |
| Dense QR codes from long URLs | Shorten URLs or use article/link QR output instead of a huge raw QR. |
| Missing diagrams on paper | Install `@mermaid-js/mermaid-cli`; preview still works for text layout. |
| Garbled Portuguese accents | Set `encoding: cp860` or `cp850` in `config/printer.yaml`. |

## When to Load References

- **Install, update, extras, printer setup** -> [references/install.md](references/install.md)
- **Agent-side safe printing and preview capture** -> [references/agent-protocol.md](references/agent-protocol.md)
- **Flags, subcommands, HTTP endpoint** -> [references/commands.md](references/commands.md)
- **How to print each content type** -> [references/printing.md](references/printing.md)
- **Markdown, frontmatter, templates, mermaid, inline QR** -> [references/templates.md](references/templates.md)
- **Anytype, Google Calendar, Google Keep, HTTP automation** -> [references/integrations.md](references/integrations.md)
- **Errors, USB, encoding, CUPS, missing deps** -> [references/troubleshooting.md](references/troubleshooting.md)

## Related Project Docs

- [docs/QUICKSTART.md](../../docs/QUICKSTART.md)
- [docs/COMMANDS.md](../../docs/COMMANDS.md)
- [docs/CONFIG.md](../../docs/CONFIG.md)
- [docs/TEMPLATES.md](../../docs/TEMPLATES.md)
