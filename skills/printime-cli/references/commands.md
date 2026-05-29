# Commands

**Intent-first CLI.** Default = terminal preview. `--print` = paper.

Run `printime <intent> --help` for flags. Top-level `printime --help` lists intents first.

## Intent commands (preferred)

### Required vs optional

| Intent | Required | Optional |
| ------ | -------- | -------- |
| `note`, `task`, `message`, `email` | `--body` or `--file` | `--title`, `--caption`, `--print`, … |
| `checklist` | `--items` or `--file` | `--title`, `--body` (intro above list), `--caption`, `--print` |
| `url`, `qr`, `ticket`, `image`, `ascii` | `TARGET` positional | intent-specific flags, `--print` |

Per-intent detail: `printime <intent> --help` (flag help + Examples epilog).

Shared on `note`, `checklist`, `task`, `message`, `email`:

| Flag | Use |
| ---- | --- |
| `--title` | Optional header (default: template name — Task, Note, Checklist, …) |
| `--body` | Main text; checklist: optional intro above list |
| `--caption` | Optional subtitle |
| `--print` | Send to printer |
| `--no-cut` | Skip cut |
| `--file`, `-f` | Context file (.md, .json, .yaml) |
| `--priority` | HIGH / MEDIUM / LOW |
| `--tags` | Comma-separated |

| Command | Extra flags |
| ------- | ----------- |
| `checklist` | `--items "A\|B::done"` (checked: `::done` or `::checked`) |
| `task` | `--due YYYY-MM-DD`, `--done` |
| `url` | `TARGET` URL, `--max-chars`, `--link-qr` |
| `qr` | `TARGET` payload, `--qr-size`, `--show-link` |
| `ticket` | `TARGET` PDF path |
| `image` | `TARGET` image path, `--title`, `--caption` |
| `ascii` | `TARGET` text, `--ascii-font`, `--center` |

### Examples

```bash
printime task --body "comer arroz hoy"
printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry"
printime url "https://example.com/article"
printime qr "https://example.com"
printime print notes.md
printime print --markdown --text "# Title\n\n- item"
```

## Legacy `print` / `preview`

For **markdown files**, **inline markdown**, advanced templates (`document`, `diagram`, `jira`, …), mermaid, and `--test` prints. Prefer intent commands for daily use.

```bash
printime print notes.md
printime print --template document --file page.md --preview
printime preview --template note --title Test --content Hello   # legacy preview-only
```

## `serve`

| Flag | Use |
| ---- | --- |
| `--port`, `-p` | Port (default 8080) |

```json
{"template":"note","context":{"title":"Hi","body":"From HTTP"}}
```

## `doctor` / `list` / integrations

`doctor`, `list`, `anytype`, `keep`, `agenda` — see [integrations.md](integrations.md).
