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

### Quick note (template)

Prefer templates for notes, messages, and checklists. They include title blocks and automatic minute-precision datetime.

```bash
printime print --template note \
  --title "Title" \
  --content "Body text" \
  --preview
```

`note`, `checklist`, `message`, and `agenda` print `YYYY-MM-DD HH:MM` below the title/subtitle automatically.

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

### Plain text fallback

```bash
printime print --text "Hello world"
printime print --text "URGENT" --bold
printime print --text "Centered" --center
printime print --text "No cut" --no-cut
```

Plain text has **no** title bar, template fields, or automatic datetime. Paper is cut at the end unless `--no-cut`.

### ASCII art

Render short receipt-safe banners locally with `pyfiglet`:

```bash
printime print --ascii "hello" --ascii-font slant --center --preview
printime print --ascii "oriel" --ascii-font pagga --preview
printime ascii-fonts
```

Use markdown fences for ASCII art inside `.md` files, `--markdown --text`, or template `--content`:

````bash
printime print --markdown --text $'```slant --center\nhello world\n```' --preview
printime print --template note --title "Today" \
  --markdown \
  --content $'```pagga --center\nhello\n```\n\nNormal text after.' \
  --preview
````

The public font choices are intentionally limited to the thermal-safe set: `pagga`, `avatar`, `bulbhead`, `banner`, and `slant`. Use `printime ascii-fonts` to list them with style notes. Local `pagga` uses pyfiglet's packaged `pagga.tlf` TOIlet font and matches the asciified API when requested as `Pagga` (the API is case-sensitive). Printime prints ASCII-art rows as one tight multiline block, like piping API output to `printime print --text`. Printime measures the rendered FIGlet output, wraps by words, and only emits lines that fit the configured paper width. If one unbroken word is too wide, Printime splits that word into multiple fitted chunks before trying compact internal fallback fonts such as `small`, `smslant`, and `mini`. Add `--ascii-api-fallback` to try the asciified web API when local rendering fails; API requests use capitalized font names such as `Pagga`.

### From markdown file

```bash
printime print my-note.md --preview
printime print examples/oriel-mandates.md --preview  # includes a rendered table
printime print examples/note.md --preview
printime print examples/diagram_flow.md --preview   # document: headings, checklist, mermaid, QR
```

Positional `FILE` is shorthand for `.md` files. Markdown tables render as receipt-friendly columns instead of raw `|` rows. Mixed markdown (body + mermaid + QR) auto-selects the `document` template.

### Enriched markdown text

Use `--markdown` for quick enriched text: headings, checkboxes, tables, links, and inline markdown.

```bash
printime print --markdown --text $'# Today\n\n**Top risks**\n\n- [ ] Ship docs\n\n| Metric | Owner | Status | Next |\n| --- | --- | --- | --- |\n| Activation | Ana | Green | Watch signups |' --preview
```

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
| ---- | ----------- |
| `--text`, `-t` | Plain text (no template) |
| `--ascii` | Render text as ASCII art |
| `--ascii-font` | Limited ASCII art font choice: `pagga`, `avatar`, `bulbhead`, `banner`, or `slant` (default `slant`) |
| `--ascii-api-fallback` | Try the asciified API if local rendering fails |
| `--ascii-strict` | Fail instead of falling back to a compact font |
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
| `--preview`, `-p` | Render terminal preview only; no paper by itself |
| `--yes`, `-y` | Print immediately, or print after `--preview` |
| `--no-cut` | Do not cut paper |
| `--bold` | Bold (with `--text`) |
| `--center` | Center (with `--text`) |
| `--test` | Test print: `qr`, `text`, `all` |

---

## preview

Show terminal preview. It does not print paper unless you also pass `--yes`.

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
printime preview --text "Raw line"
```

Preview behavior is explicit:

| Command form | Behavior |
| ------------ | -------- |
| `printime print notes.md --preview` | Show preview only; no paper. |
| `printime print notes.md --preview --yes` | Show preview, then print paper. |
| `printime print notes.md --yes` | Print paper immediately without preview. |

---

## list

```bash
printime list
printime list document
```

Templates: `note`, `checklist`, `document`, `diagram`, `task`, `jira`, `message`, `receipt`, `heading`, `agenda`, `equation`

---

## ascii-fonts

List the limited thermal-safe ASCII art fonts available for `--ascii-font` and markdown fences.

```bash
printime ascii-fonts
```

Public font choices are limited to `pagga`, `avatar`, `bulbhead`, `banner`, and `slant`. Wider or noisy FIGlet fonts such as `shadow`, `thin`, `varsity`, `banner3`, `sub-zero`, and `the-edge` are not exposed because they do not fit 48-column thermal receipts reliably.

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
printime agenda --today --preview
printime agenda --preview
printime agenda --yes
printime agenda --days 3 --preview
printime agenda --days 7 --preview
printime agenda --next-week --yes
printime agenda --ics-url 'https://calendar.google.com/calendar/ical/...'
```

`--today` is the explicit default one-day agenda. `--days 7` prints this week from today; `--next-week` prints the upcoming Mon-Sun week. Agenda output includes event title, time, location, and notes/details from the calendar description when present.

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
