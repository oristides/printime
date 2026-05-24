# Commands

Full CLI reference for `printime`.

```bash
printime --help
printime <command> --help
```

## Global

```bash
printime --version
```

## print

Print text, QR codes, templates, or markdown files.

```bash
printime print [OPTIONS] [FILE]
```

### Quick note (inline)

```bash
printime print --template note \
  --title "Title" \
  --content "Body text" \
  --preview
```

### From markdown file

```bash
printime print my-note.md --preview
printime print --md my-note.md --preview    # same thing
```

The positional `FILE` argument is shorthand for `.md` files:

```bash
printime print examples/note.md --preview
```

### Template + context file

```bash
printime print --template note --file examples/note.md --preview
printime print --template checklist --file examples/checklist.md --preview
```

Context files can be `.md`, `.json`, or `.yaml`.

### Plain text and QR

```bash
printime print --text "Hello world"
printime print --text "Bold" --bold
printime print --text "Centered" --center
printime print --qr "https://example.com"
```

### Flags

| Flag | Description |
|------|-------------|
| `--template`, `-t` | Template name (`note`, `checklist`, `task`, …) |
| `--title` | Title (with `--template`, no `--file`) |
| `--content` | Body text (with `--template`, no `--file`) |
| `--priority` | Priority label (`HIGH`, `MEDIUM`, `LOW`) |
| `--tags` | Comma-separated tags |
| `--file`, `-f` | Context file (`.md`, `.json`, `.yaml`) |
| `--md` | Markdown file to print |
| `--preview`, `-p` | Show preview and confirm before printing |
| `--yes`, `-y` | Skip confirmation prompt |
| `--no-cut` | Do not cut paper after printing |
| `--bold` | Bold text (with `--text`) |
| `--center` | Center align (with `--text`) |
| `--test` | Run test print (`qr`, `text`, or `all`) |

## preview

Show terminal preview without printing (unless you confirm).

```bash
printime preview --file examples/note.md
printime preview --template note --title "Test" --content "Hello"
printime preview --text "Raw preview line"
```

If you confirm at the prompt, it will print. Use preview-only workflow by declining, or pipe/redirect output.

## list

List available templates and descriptions.

```bash
printime list
```

## transform

Convert a file to template context (JSON) or render through a template.

```bash
# Show extracted context as JSON
printime transform examples/note.md

# Preview with a template
printime transform examples/note.md --template note --preview

# Save context to a file
printime transform examples/note.md -o context.json
```

Supports `.md` (→ context), `.tex` (→ image, requires LaTeX tools), and plain text.

## doctor

Diagnose printer configuration and connectivity.

```bash
printime doctor
printime doctor --test-print
```

## serve

Start an HTTP server for webhook-style printing.

```bash
printime serve --port 8080
```

**POST** `http://localhost:8080/print`

```json
{
  "text": "Hello",
  "qr": "https://example.com",
  "cut": true,
  "template": "note",
  "context": {"title": "Hi", "content": "From webhook"}
}
```

**GET** `http://localhost:8080/health` — health check.

## agenda

Print today's Google Calendar using a private ICS URL. Full guide: **[GCAL.md](GCAL.md)**.

```bash
# Add to .env first:
# GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/.../basic.ics

printime agenda --preview
printime agenda --yes
printime agenda --days 3 --preview
```

## anytype

Fetch and print pages from Anytype. Full guide: **[ANYTYPE.md](ANYTYPE.md)**.

```bash
anytype service start
anytype auth create printime   # first time only
anytype auth login             # paste base64 account key when prompted
```

Add to `.env`:

```env
ANYTYPE_API_KEY=...
ANYTYPE_SPACE_ID=bafyrei...
```

```bash
printime anytype list
printime anytype fetch <object-id> --template note --preview
```

## Typical workflows

### Daily quick note

```bash
printime print --template note \
  --title "Today" \
  --content "Finish report, gym at 6pm" \
  --preview
```

### Note from file

```bash
printime print ~/notes/today.md --preview
```

### Shopping list

```bash
printime print ~/lists/shopping.md --preview
```

### Preview first, print later

```bash
printime preview --file ~/notes/today.md
# review output, then:
printime print ~/notes/today.md --yes
```
