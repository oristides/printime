# Commands

Run help when unsure:

```bash
printime --help
printime print --help
printime anytype --help
```

Invalid commands and unknown flags print suggestions plus relevant help.

## Global

```bash
printime --version
```

## `print`

Primary command for physical output.

```bash
printime print [OPTIONS] [FILE]
```

Positional `FILE` routing:

| File type | Behavior |
| --------- | -------- |
| `.md` | Markdown input; auto-detects template. |
| `.pdf` | Ticket PDF input. |
| `.json`, `.yaml`, `.yml` | Template context file. |

Common flags:

| Flag | Use |
| ---- | --- |
| `--text`, `-t` | Plain or markdown text. |
| `--markdown`, `-m` | Parse `--text` / `--content` as markdown. |
| `--link-qr` | Add mini QR codes for URLs in markdown/text. |
| `--ticket` | Print ticket PDF. Positional `.pdf` also works. |
| `--url` | Fetch and print a web article. |
| `--qr` | Print a standalone QR page. |
| `--qr-size` | QR module size 4-12, default 8. |
| `--show-link` | Print URL text below standalone QR. |
| `--template` | Force a template. |
| `--file`, `-f` | Context file (`.md`, `.json`, `.yaml`). |
| `--md` | Explicit markdown file. |
| `--image` | Print PNG/JPG. |
| `--mermaid` | Render `.mmd` and print image. |
| `--max-chars` | URL article limit; `0` means no limit. |
| `--preview`, `-p` | Preview before printing. |
| `--yes`, `-y` | Skip confirmation. |
| `--no-cut` | Do not cut paper. |
| `--test` | `qr`, `text`, or `all`. |

Examples:

```bash
printime print --template note --title "Today" --content "Ship docs" --preview
printime print --template message --title "Alert" --content "Printer ready" --preview
printime print notes.md --preview
printime print examples/oriel-mandates.md --preview
printime print --markdown --text $'# Today\n\n**Top risks**\n\n| Metric | Owner | Status | Next |\n| --- | --- | --- | --- |\n| Activation | Ana | Green | Watch signups |' --preview
printime print ticket.pdf --preview
printime print --url "https://example.com/article" --preview
printime print --qr "https://example.com" --qr-size 10 --show-link
printime print --text "Hello"  # raw text fallback only
```

## `preview`

Render terminal output and optionally confirm a print.

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
printime preview --text "Raw line"
```

## `list`

List templates or fields for a template.

```bash
printime list
printime list --verbose
printime list document
```

## `transform`

Convert input to context/text/image, or preview through a template.

```bash
printime transform examples/note.md
printime transform examples/note.md --template note --preview
printime transform examples/note.md -o context.json
printime transform --url "https://example.com" --template note --preview
```

## `doctor`

Diagnose printer and optionally print a test page.

```bash
printime doctor
printime doctor --test-print
```

## `serve`

Start a local HTTP server for automation.

```bash
printime serve --port 8080
```

Health check:

```bash
curl http://localhost:8080/health
```

Print endpoint:

```bash
curl -X POST http://localhost:8080/print \
  -H 'Content-Type: application/json' \
  -d '{"template":"note","context":{"title":"Hi","content":"From HTTP"}}'
```

Use only on trusted LAN/Tailscale networks; there is no auth.

## `agenda`

Print Google Calendar from a private ICS URL.

```bash
printime agenda --today --preview
printime agenda --preview
printime agenda --days 3 --preview
printime agenda --days 7 --preview
printime agenda --next-week --yes
printime agenda --ics-url "https://calendar.google.com/calendar/ical/..."
```

`--today` is the explicit form of the default one-day agenda. Agenda output includes event time, title, location, and notes/details from the ICS description when present.

## `anytype`

Search and print Anytype Desktop pages.

```bash
printime anytype list
printime anytype search "Login"
printime anytype print "Login Flow" --preview
printime anytype print "Login Flow" --template note --preview
printime anytype fetch <object-id> --preview
printime anytype join "<invite-link>"
```

## `keep`

Search and print Google Keep notes.

```bash
printime keep list
printime keep search "shopping"
printime keep print "https://keep.google.com/#NOTE/abc..." --preview
printime keep print "abc..." --yes
```
