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

**If you want all your spaces and pages (including "I am 021er"), use the Desktop API.**

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
printime anytype fetch bafyrei...page-id... --template note --preview
```

### Bot CLI setup (automation / headless only)

Use this only if you need a background bot without Desktop open. Requires joining each space via invite link (`https://...#...` with `cid` and `key` after `#`).

**Not valid for join:** profile URLs like `https://any.coop/AA1Yc2.../i-am-021er`

## What you can print from Anytype

Anytype pages are fetched via the local Anytype HTTP API, converted to plain text/markdown, then rendered through a printime template (`note` by default).

Works well for:

- Notes and documents → `note` template
- Tasks → `task` template (auto-detected)
- Pages with checkboxes → `checklist` template (auto-detected from markdown body)

## One-time setup

### 1. Install and start Anytype CLI

```bash
anytype service start
anytype service status    # should show running
```

### 2. Create a bot account (first time)

The Anytype CLI **does not** accept your normal Anytype recovery phrase. It uses a separate **bot account**:

```bash
anytype auth create printime
```

This prints a long **base64 account key** (one line, ends with `=`). Save it somewhere safe.

To log in later, pass that **string** — not a file path:

```bash
anytype auth login --account-key 'paste-the-base64-key-here'
```

Or paste when prompted:

```bash
anytype auth login
# Enter account key: <paste>
```

Wrong (causes "must be valid base64"):

```bash
anytype auth login --account-key ~/.anytype/account.key   # path is not read as a file
```

If you already have the key in a file:

```bash
anytype auth login --account-key "$(cat ~/path/to/account.key)"
```

Verify:

```bash
anytype auth status
```

### 3. Join every space you want to print from

The bot account **cannot** see your Anytype Desktop vault automatically. It only sees spaces it has **joined**.

For each space (Personal, Work, etc.):

1. Open the space in **Anytype Desktop**
2. **Share** → copy the invite link
3. Run:

```bash
anytype space join 'https://...invite-link...'
```

Repeat for each space. Then list them all:

```bash
printime anytype list
anytype space list
```

You do **not** need `ANYTYPE_SPACE_ID` in `.env` anymore — printime searches all joined spaces when fetching a page. Set it only if you want to prefer one space first.

### 4. Create an API key (if you don't have one)

In Anytype Desktop, approve the auth challenge, or:

```bash
anytype auth apikey create my-printime-key
```

Add to `printime/.env`:

```env
ANYTYPE_API_KEY=your-api-key-here
# ANYTYPE_SPACE_ID=...   # optional — prefer this space when searching
ANYTYPE_API_URL=http://127.0.0.1:31012
```

### 5. Find a page (object) ID

In Anytype Desktop:

1. Open the page you want to print
2. Open object details / properties
3. Copy the **object ID** (a long `bafyrei...` string)

The object ID is **not** the page title — it is a unique identifier for that object in your space.

## Print an Anytype page

```bash
cd ~/Documents/repos/random_projects/adhd/printime
source .venv/bin/activate

# Preview first (recommended)
# Auto-search all joined spaces (default)
printime anytype fetch bafyrei...object-id... --template note --preview

# Or target one space explicitly
printime anytype fetch bafyrei...object-id... --space bafyrei...space-id... --preview
```

### Choose a template

| Anytype content | Suggested template |
|-----------------|-------------------|
| General page / note | `note` (default) |
| Task | `task` |
| List with checkboxes | `checklist` |
| Ticket-style page | `jira` |

```bash
printime anytype fetch <object-id> --template task --preview
printime anytype fetch <object-id> --template checklist --preview
```

## Workaround: export to markdown

If Anytype auth is not set up yet, copy the page content into a `.md` file and print normally:

```bash
printime print my-anytype-page.md --preview
```

This uses the same markdown workflow as other notes. See [QUICKSTART.md](QUICKSTART.md).

## Troubleshooting

### `Not authenticated. Run anytype auth login`

The CLI is not logged in. Use your **account key**, not `ANYTYPE_API_KEY`:

```bash
anytype auth login --account-key "$(cat ~/path/to/keyfile)"
```

### `API connection error` / port 31012 not reachable

The HTTP API only starts after successful login:

```bash
anytype auth status
anytype service status
```

### `ANYTYPE_API_KEY not set`

Add the key to `.env` and reload:

```bash
set -a && source .env && set +a
```

### `404` on fetch

- Verify `ANYTYPE_SPACE_ID` matches the space containing the page
- Verify the object ID is correct (copy from Anytype, not the URL slug)

### API key vs account key

| Credential | Used for |
|------------|----------|
| **Account key** | `anytype auth login` — starts local API |
| **API key** (`ANYTYPE_API_KEY`) | HTTP requests to fetch objects |

You need **both**: login first, then use the API key for fetch requests.

## Example full workflow

```bash
anytype service start
anytype auth create printime                # first time: save the base64 key
anytype auth login --account-key '<base64-key>'
anytype space join '<invite-link-from-desktop>'
anytype space list                          # copy space ID → .env

printime anytype fetch bafyreie6n5l5nkbjal37su54cha4coy7qzuhrnajluzv5qd5jvtsrxkequ \
  --template note \
  --preview
```
