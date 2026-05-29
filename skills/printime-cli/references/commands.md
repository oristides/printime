# Commands

**This file contains:** full flag tables per subcommand, positional file routing, and HTTP `serve` payload shapes. Examples and the preview/print contract are in [SKILL.md](../SKILL.md) §2 and §5 — load this file when you need an exact flag name or API body.

Run `printime <command> --help` for live help; typos print suggestions.

## Global

| Flag | Use |
| ---- | --- |
| `--version`, `-v` | CLI version |

## `print`

```text
printime print [OPTIONS] [FILE]
```

Positional `FILE` routing:

| File type | Behavior |
| --------- | -------- |
| `.md` | Markdown; auto-detects template (see SKILL.md §4) |
| `.pdf` | Ticket PDF |
| `.json`, `.yaml`, `.yml` | Template context file |

| Flag | Use |
| ---- | --- |
| `--file`, `-f` | Context file (`.md`, `.json`, `.yaml`) |
| `--md` | Explicit markdown file |
| `--text`, `-t` | Plain or markdown text |
| `--markdown`, `-m` | Parse `--text` / `--content` as markdown |
| `--template` | Force template: `note`, `checklist`, `document`, `diagram`, `task`, `jira`, `message`, `email`, `receipt`, `heading`, `agenda`, `equation`, `ticket` — `printime list <name>` for fields |
| `--title` | Template title |
| `--content` | Template body |
| `--items` | Checklist list: `Milk\|Bread::x\|Eggs` (pipe-separated; checked: `::x`) |
| `--priority` | `HIGH`, `MEDIUM`, `LOW` |
| `--tags` | Comma-separated tags |
| `--url` | Fetch and print web article |
| `--max-chars` | URL limit; `0` = no limit (default 12000) |
| `--ticket` | Ticket PDF path (positional `.pdf` equivalent) |
| `--image` | PNG/JPG file |
| `--mermaid` | Render `.mmd` via mermaid-cli |
| `--qr` | Standalone QR page |
| `--qr-size` | Module size 4–12 (default 8) |
| `--show-link` | URL text below standalone QR |
| `--link-qr` | Mini QRs for URLs in markdown/articles |
| `--bold` | Bold text |
| `--center` | Center align |
| `--double-height` | Double-height text |
| `--ascii` | ASCII art banner |
| `--ascii-font` | `pagga`, `avatar`, `bulbhead`, `banner`, `slant` |
| `--ascii-api-fallback` | asciified API if local render fails |
| `--ascii-strict` | Fail instead of compact font fallback |
| `--preview`, `-p` | Terminal preview only |
| `--yes`, `-y` | Print immediately or after preview |
| `--no-cut` | Skip paper cut |
| `--test` | `qr`, `text`, or `all` |

## `preview`

| Flag | Use |
| ---- | --- |
| `--text`, `-t` | Text to preview |
| `--template` | Template name |
| `--title`, `--content` | Template fields |
| `--items` | Checklist list: `Milk\|Bread::x` |
| `--file`, `-f` | Context file |
| `--yes`, `-y` | Print after preview |
| `--no-cut` | Skip cut |

## `list`

| Arg / flag | Use |
| ---------- | --- |
| `[template]` | Fields for one template |
| `--verbose`, `-v` | All templates with fields |

## `ascii-fonts`

Lists thermal-safe fonts for `--ascii-font` and markdown fences (no flags).

## `transform`

| Flag | Use |
| ---- | --- |
| `input` | `.md`, `.tex`, `.txt` |
| `--type`, `-t` | `context`, `text`, `image` (auto from extension) |
| `--template` | Wrap output in template |
| `--output`, `-o` | Output file (default stdout) |
| `--url` | Fetch article instead of local file |
| `--max-chars` | URL limit |
| `--preview`, `-p` | Preview only |
| `--yes`, `-y` | Print after preview |

## `doctor`

| Flag | Use |
| ---- | --- |
| `--test-print` | Send test page |

## `serve`

| Flag | Use |
| ---- | --- |
| `--port`, `-p` | Port (default 8080) |

**Health:** `GET /health`

**Print template:**

```json
{"template":"note","context":{"title":"Hi","content":"From HTTP"}}
```

**Print checklist:**

```json
{"template":"checklist","context":{"title":"Today","items":[{"text":"Milk","checked":false},{"text":"Bread","checked":true}]}}
```

**Print email:**

```json
{"template":"email","context":{"subject":"Deploy","sender":"ana@co.com","to":"you@co.com","body":"Review before 6pm."}}
```

**Raw text + QR:**

```json
{"text":"Hello","qr":"https://example.com","cut":true}
```

No auth — localhost, LAN, or Tailscale only.

## `agenda`

| Flag | Use |
| ---- | --- |
| `--today` | Today's events (default window) |
| `--days N` | Next N days from today |
| `--next-week` | Mon–Sun of next calendar week |
| `--ics-url` | Override `GOOGLE_CALENDAR_ICS_URL` |
| `--preview`, `-p` | Preview only |
| `--yes`, `-y` | Print |

Event output: time, title, location, notes from ICS description when present.

## `anytype`

| Subcommand | Use |
| ---------- | --- |
| `list` | Spaces / pages |
| `search "query"` | Search pages |
| `print "Title"` | Print by page title |
| `fetch <object-id>` | Print by ID |
| `join "<invite>"` | Bot API: join space |

Flags on `print` / `fetch`: `--template`, `--preview`, `--yes`, `--no-cut`.

## `keep`

| Subcommand | Use |
| ---------- | --- |
| `list` | Notes |
| `search "query"` | Search |
| `print "URL or ID"` | Print note |

Flags: `--preview`, `--yes`. Keep URLs need `keep print`, not `print --url`.
