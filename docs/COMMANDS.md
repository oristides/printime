# Commands

Full CLI reference for `printime`.

```bash
printime --help
printime <command> --help
```

**Typos:** invalid commands and unknown flags print a suggestion plus the relevant `--help` (e.g. `prnt` → `print`, `--titel` → `--title`).

## Global

```bash
printime --version
```

---

## print

Print text, QR codes, templates, markdown, URLs, or files.

```bash
printime print [OPTIONS] [FILE]
```

### Plain text

```bash
printime print --text "Hello world"
printime print --text "URGENT" --bold
printime print --text "Centered" --center
printime print --text "No cut" --no-cut
```

Plain text has **no** title bar or template borders. Paper is cut at the end unless `--no-cut`.

### QR codes

Large centered QR with `SCAN ME` header (URL text below is **off** by default):

```bash
printime print --qr "https://example.com"
printime print --qr "https://..." --qr-size 10       # larger (4–12, default 8)
printime print --qr "https://..." --show-link        # print URL under QR
printime print --qr 'WIFI:T:WPA;S:SSID;P:pass;;'     # WiFi join slip
```

Long URLs (>300 chars): shorten first (bit.ly) — dense QR codes scan poorly.

### Web articles

```bash
printime print --url 'https://www.example.com/article' --preview
printime print --url 'https://...' --max-chars 3000  # shorter excerpt (default 12000)
printime print --url 'https://...' --max-chars 0     # no limit
```

Works well: Substack, many news sites (Folha `articleBody`). Unreliable: Medium, paywalls.

### Quick note (template)

```bash
printime print --template note \
  --title "Title" \
  --content "Body text" \
  --preview
```

### From markdown file

```bash
printime print my-note.md --preview
printime print examples/note.md --preview
printime print examples/diagram_flow.md --preview   # document: headings, checklist, mermaid, QR
```

Positional `FILE` is shorthand for `.md` files. Mixed markdown (body + mermaid + QR) auto-selects the `document` template.

### Images and diagrams

```bash
printime print --image photo.png --preview
printime print --mermaid flow.mmd --preview          # needs mermaid-cli
```

Markdown can embed mermaid and QR inline — see [TEMPLATES.md](TEMPLATES.md).

### Template + context file

```bash
printime print --template note --file examples/note.md --preview
printime print --template checklist --file examples/checklist.md --preview
```

Context files: `.md`, `.json`, `.yaml`.

### Test prints

```bash
printime print --test qr
printime print --test text
printime print --test all
```

### print flags

| Flag | Description |
|------|-------------|
| `--text`, `-t` | Plain text (no template) |
| `--qr` | Print QR payload (URL, WiFi, vCard, etc.) |
| `--qr-size` | QR module size 4–12 (default **8**) |
| `--show-link` | Print URL text below QR |
| `--url` | Fetch and print a web article |
| `--image` | Print a PNG/JPG image file |
| `--mermaid` | Render a `.mmd` file and print (mermaid-cli) |
| `--max-chars` | Max chars for `--url` (default **12000**, `0` = unlimited) |
| `--template`, `-t` | Template name |
| `--title` | Title (with `--template`, no `--file`) |
| `--content` | Body (with `--template`, no `--file`) |
| `--priority` | `HIGH`, `MEDIUM`, `LOW` |
| `--tags` | Comma-separated tags |
| `--file`, `-f` | Context file |
| `--md` | Markdown file |
| `--preview`, `-p` | Preview and confirm |
| `--yes`, `-y` | Skip confirmation |
| `--no-cut` | Do not cut paper |
| `--bold` | Bold (with `--text`) |
| `--center` | Center (with `--text`) |
| `--test` | Test print: `qr`, `text`, `all` |

---

## preview

Show terminal preview. Confirms before printing unless you decline.

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
printime preview --text "Raw line"
```

---

## list

```bash
printime list
printime list document
```

Templates: `note`, `checklist`, `document`, `diagram`, `task`, `jira`, `message`, `receipt`, `heading`, `agenda`, `equation`

---

## transform

Convert files to template context JSON, or preview/print through a template.

```bash
printime transform examples/note.md
printime transform examples/note.md --template note --preview
printime transform examples/note.md -o context.json
printime transform --url 'https://...' --template note --preview
```

Supports `.md` → context, `.tex` → image (needs LaTeX), plain text.

---

## doctor

```bash
printime doctor
printime doctor --test-print
```

Expect: `backend: usb`, `USB device: found`, `CUPS status: idle` (idle = ready).

---

## serve

HTTP server for webhook-style printing (no auth — LAN/Tailscale only).

```bash
printime serve --port 8080
```

**POST** `http://localhost:8080/print`

```json
{
  "text": "Hello",
  "qr": "WIFI:T:WPA;S:Guest;P:pass;;",
  "cut": true,
  "template": "note",
  "context": {"title": "Hi", "content": "From webhook"}
}
```

**GET** `http://localhost:8080/health`

Note: `serve` QR uses simple mode (not the full `SCAN ME` layout from CLI `--qr` yet).

For desktop shortcuts, see [HOTKEYS.md](HOTKEYS.md).

---

## agenda

Google Calendar via private ICS URL in `.env`. See [GCAL.md](GCAL.md).

```bash
printime agenda --preview
printime agenda --yes
printime agenda --days 3 --preview
printime agenda --next-week --yes
printime agenda --ics-url 'https://calendar.google.com/calendar/ical/...'
```

---

## anytype

Print Anytype pages. See [ANYTYPE.md](ANYTYPE.md). **Desktop API (port 31009) recommended.**

```bash
printime anytype list
printime anytype search "query"
printime anytype print "Page title" --preview
printime anytype print "Login Flow" --preview     # auto document layout
printime anytype print "Page title" --yes
printime anytype fetch <object-id> --template note --preview
printime anytype join '<invite-link>'
printime anytype --help                             # subcommands + examples
```

Rich pages (headings + checkboxes + diagram + QR) auto-use the `document` template. Page **name** is the print title unless YAML frontmatter sets `title`/`caption`.

`.env`:

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

---

## Typical workflows

### Plain reminder

```bash
printime print --text "Take medication at 2pm"
```

### Daily note

```bash
printime print --template note \
  --title "Today" \
  --content "Finish report, gym at 6pm" \
  --preview
```

### Morning routine (cron)

```cron
0 7 * * 1-5 printime agenda --yes
0 7 * * 1-5 printime anytype print "Today" --yes
```

Use full path if cron lacks PATH: `/home/oriel/.local/bin/printime`
