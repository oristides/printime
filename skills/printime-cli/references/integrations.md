# Integrations

**This file contains:** Anytype, Google Calendar ICS, Google Keep, and HTTP `serve` setup — env vars, ports, and command flags.

## Anytype

**Prefer Desktop API** (`http://127.0.0.1:31009`) with Anytype Desktop running. Use **Bot API** (`31012`) only for headless automation after joining spaces.

`.env`:

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

| Command | Use |
| ------- | --- |
| `printime anytype list` | Spaces / pages |
| `printime anytype search "Login Flow"` | Search |
| `printime anytype print "Login Flow" --preview` | Print by title |
| `printime anytype fetch <object-id> --preview` | Print by ID |

Rich pages auto-select `document` when they have headings, checkboxes, diagrams, or QR blocks. Page name → title unless frontmatter overrides.

### Bot API (headless only)

```env
ANYTYPE_API_URL=http://127.0.0.1:31012
```

```bash
printime anytype join "<invite-link>"
```

## Google Calendar

Private ICS URL — no OAuth. Treat URL like a password.

`.env`:

```env
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/.../private-.../basic.ics
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
```

| Flag | Use |
| ---- | --- |
| `--today` | Today (default window) |
| `--days N` | Next N days |
| `--next-week` | Next Mon–Sun |
| `--ics-url` | Override env URL |
| `--preview` / `--yes` | Preview / print |

Agenda prints auto datetime under title; events include time, title, location, notes from ICS description.

## Google Keep

Requires `gkeepapi` — **not** `printime print --url` (Keep URLs use fragments).

```bash
pipx inject printime gkeepapi
```

`.env`:

```env
GOOGLE_KEEP_EMAIL=you@gmail.com
GOOGLE_KEEP_MASTER_TOKEN=your-master-token-here
GOOGLE_KEEP_STATE_PATH=~/.cache/printime/keep-state.json
```

| Command | Use |
| ------- | --- |
| `printime keep list` | Notes |
| `printime keep search "shopping"` | Search |
| `printime keep print "https://keep.google.com/#NOTE/..." --preview` | Print |

Master token = full account access. Never commit `.env`.

## HTTP Automation

```bash
printime serve --port 8080
```

`GET /health` — `POST /print` with JSON body (see [commands.md](commands.md) for payloads).

No auth — localhost, LAN, or Tailscale only.
