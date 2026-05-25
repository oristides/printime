# Google Keep

Print notes from Google Keep by **note URL or ID**. This uses the unofficial [`gkeepapi`](https://github.com/kiwiz/gkeepapi) library (works with personal `@gmail.com` accounts).

**`printime print --url` does not work for Keep** — Google requires login and the note ID lives in the URL hash (`#NOTE/...`), which never reaches the server.

## Quick start

```bash
# 1. Install Keep support
pipx inject printime gkeepapi

# 2. Add credentials to .env (see below)
cp .env.example .env

# 3. Print your note
printime keep print "https://keep.google.com/#NOTE/1_hjNNZwcXIdKUqjQ8stzfreTy0BgG1flZEjaxBiflc6qMSbM6ihWDTigNaOZFmVCq3d1" --preview
```

## Setup (one time)

### 1. Obtain a Google master token

`gkeepapi` uses a **master token** (full account access — treat like a password).

**Docker one-liner** (from [gkeepapi docs](https://gkeepapi.readthedocs.io/en/latest/)):

```bash
docker run --rm -it --entrypoint /bin/sh python:3 -c \
  'pip install gpsoauth; python3 -c '"'"'print(__import__("gpsoauth").exchange_token(input("Email: "), input("OAuth Token: "), input("Android ID: ")))'"'"''
```

You will need:

- Your Gmail address
- An OAuth token from Google (see [gpsoauth](https://github.com/simon-weber/gpsoauth))
- An Android ID (any 16-char hex string is often used for personal scripts)

The output JSON contains `"Token":"..."` — that is your master token.

### 2. Add to `.env`

```env
GOOGLE_KEEP_EMAIL=you@gmail.com
GOOGLE_KEEP_MASTER_TOKEN=your-master-token-here

# Optional: cache sync state for faster later runs
GOOGLE_KEEP_STATE_PATH=~/.cache/printime/keep-state.json
```

Never commit `.env`.

## Commands

```bash
printime keep print "https://keep.google.com/#NOTE/abc123..." --preview
printime keep print "abc123..." --yes                    # by note ID only
printime keep search "shopping"                          # find by title/text
printime keep list                                       # recent notes + IDs
printime keep --help
```

Printed output includes:

- Title and body (with **cp860** Portuguese support if configured)
- Checklists as `[ ]` / `[X]` items
- **Mini QR codes** for URLs in the note (same as markdown / Anytype)
- Optional main QR for the Keep URL

## Workspace Enterprise

If you have **Google Workspace Enterprise**, Google offers an [official Keep API](https://developers.google.com/workspace/keep/api/reference/rest). That is not wired into printime yet; personal accounts should use `gkeepapi` above.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `requires gkeepapi` | `pipx inject printime gkeepapi` |
| `Set GOOGLE_KEEP_EMAIL` | Add credentials to `.env` |
| Auth failed | Regenerate master token; check 2FA / app password |
| Note not found | Copy URL from Keep while note is open; try `keep search "title"` |
| `--url` on Keep link fails | Use `keep print`, not `--url` |
| Slow first sync | Set `GOOGLE_KEEP_STATE_PATH` to cache notes locally |

## Privacy

Master token = full Google account access. Store in `.env` or a secrets manager only.
