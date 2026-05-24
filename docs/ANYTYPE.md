# Anytype integration

Print pages from Anytype directly to your thermal printer.

## Which API should you use?

| | **Desktop API** (recommended) | **Bot CLI API** |
|---|---|---|
| Port | `31009` | `31012` |
| Account | **Your** Anytype Desktop login | Separate bot account |
| Sees all your pages? | **Yes** | No — must join each space |
| API key from | Desktop → **Settings → API Keys** | `anytype auth apikey create` |
| Needs `space join`? | **No** | Yes, per space |

**If you want all your spaces and pages, use the Desktop API.**

### Desktop API setup (all spaces)

1. Open **Anytype Desktop** (keep it running)
2. **Settings → API Keys → Create new**
3. Copy the key into `.env`:

```env
ANYTYPE_API_KEY=your-desktop-api-key-here
ANYTYPE_API_URL=http://127.0.0.1:31009
```

4. Search and print — no invite links, no bot account:

```bash
printime anytype list
printime anytype search "Login Flow"
printime anytype print "Login Flow" --preview
printime anytype fetch bafyrei...page-id... --preview
```

## What you can print from Anytype

Anytype pages are fetched via the local HTTP API, normalized to markdown, then rendered through printime templates.

| Page content | Template (auto) |
|--------------|-----------------|
| Headings + body + checkboxes + diagram + QR | `document` |
| Mermaid / diagram only | `diagram` |
| Checkboxes only | `checklist` |
| Simple note | `note` |
| Task object | `task` |

Override with `--template`:

```bash
printime anytype print "My page" --template note --preview
```

### Title and caption

- **Page name** (e.g. "Login Flow") becomes the print title when there is no YAML frontmatter.
- A `# Heading` in the body does **not** override the page name.
- For a **caption** under the title, paste YAML frontmatter at the top of the Anytype page:

```yaml
---
title: Login Flow
caption: Happy path only
---
```

### Paste / export quirks (handled automatically)

Anytype’s API may return markdown with:

- Escaped backticks: `\`\`\`qr` → restored to ` ```qr `
- Tight checkboxes: `-[x] Bread` → `- [x] Bread`
- Plain code fences for mermaid (no `mermaid` tag) — detected by `graph TD`, `flowchart`, etc.
- Unicode arrows (`—>`) and merged lines in diagrams — normalized before render

Compare output:

```bash
printime print examples/diagram_flow.md --preview
printime anytype print "Login Flow" --preview
```

## Commands

```bash
printime anytype list                              # spaces
printime anytype search "query"                    # find pages
printime anytype print "Page title" --preview      # search + print best match
printime anytype print "Page title" --yes          # skip confirmation
printime anytype fetch <object-id> --preview       # by ID
printime anytype join '<invite-link>'              # bot API only
printime anytype --help                            # subcommands
```

## Bot CLI setup (automation / headless only)

Use this only if you need a background bot without Desktop open.

```bash
anytype service start
anytype auth create printime
anytype auth login --account-key 'paste-the-base64-key-here'
anytype space join 'https://...invite-link...'
```

```env
ANYTYPE_API_URL=http://127.0.0.1:31012
ANYTYPE_API_KEY=your-bot-api-key
```

## Workaround: export to markdown

Copy page content into a `.md` file and print normally:

```bash
printime print my-anytype-page.md --preview
```

## Troubleshooting

### `Not authenticated. Run anytype auth login`

Bot CLI only — use your **account key**, not `ANYTYPE_API_KEY`:

```bash
anytype auth login --account-key "$(cat ~/path/to/keyfile)"
```

### `ANYTYPE_API_KEY not set`

Add the key to `.env` in the printime repo root.

### Wrong template / missing diagram or QR

Update printime (`pipx reinstall printime`). Rich pages should use `document`. If mermaid fails to render, install mermaid-cli:

```bash
npm install -g @mermaid-js/mermaid-cli
```

### No caption on print

Anytype paste does not include frontmatter — add `caption:` in YAML at the top of the page (see above).

### API key vs account key

| Credential | Used for |
|------------|----------|
| **Account key** | `anytype auth login` — starts local API (bot CLI) |
| **API key** (`ANYTYPE_API_KEY`) | HTTP requests to fetch objects |

Desktop API: only the API key from Desktop settings is needed.

## Example workflow

```bash
# Desktop API
printime anytype search "Login Flow"
printime anytype print "Login Flow" --preview
printime anytype print "Login Flow" --yes
```
