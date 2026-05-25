# Integrations

## Anytype

Use the Anytype Desktop API when possible.

`.env`:

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

Anytype Desktop must be running.

Commands:

```bash
printime anytype list
printime anytype search "Login Flow"
printime anytype print "Login Flow" --preview
printime anytype print "Login Flow" --template note --preview
printime anytype fetch <object-id> --preview
```

Rich Anytype pages auto-select `document` when they contain headings, checkboxes, diagrams, or QR blocks. The page name becomes the print title unless YAML frontmatter supplies `title` or `caption`.

Bot API (`http://127.0.0.1:31012`) is only for headless automation and requires joining spaces:

```bash
printime anytype join "<invite-link>"
```

## Google Calendar

Uses a private ICS link; no OAuth.

`.env`:

```env
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/.../private-.../basic.ics
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
```

Commands:

```bash
printime agenda --today --preview       # today's agenda
printime agenda --preview               # same default as --today
printime agenda --days 3 --preview
printime agenda --days 7 --preview      # this week from today
printime agenda --next-week --yes       # next Mon-Sun week
printime agenda --ics-url "https://calendar.google.com/calendar/ical/..."
```

Agenda prints a generated `YYYY-MM-DD HH:MM` line below the title. Event output includes time, title, location, and notes/details from the ICS description when present.

Treat the ICS URL like a password.

## Google Keep

Keep notes require `gkeepapi`; regular `printime print --url` cannot access Keep note fragments.

Install:

```bash
pipx inject printime gkeepapi
```

`.env`:

```env
GOOGLE_KEEP_EMAIL=you@gmail.com
GOOGLE_KEEP_MASTER_TOKEN=your-master-token-here
GOOGLE_KEEP_STATE_PATH=~/.cache/printime/keep-state.json
```

Commands:

```bash
printime keep list
printime keep search "shopping"
printime keep print "https://keep.google.com/#NOTE/abc..." --preview
printime keep print "abc..." --yes
```

The Google Keep master token is full account access. Never commit it.

## HTTP Automation

Start the server:

```bash
printime serve --port 8080
```

Health:

```bash
curl http://localhost:8080/health
```

Print a template:

```bash
curl -X POST http://localhost:8080/print \
  -H 'Content-Type: application/json' \
  -d '{"template":"note","context":{"title":"Hi","content":"From HTTP"}}'
```

Simple QR/text/raw payload:

```bash
curl -X POST http://localhost:8080/print \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello","qr":"https://example.com","cut":true}'
```

The HTTP server has no auth. Use it only on localhost, LAN, or Tailscale where access is controlled externally.
