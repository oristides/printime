# Native integration (Anytype, Ctrl+P, system print)

## Can I use Ctrl+P in Anytype?

**Not with printime templates today.**

Anytype Desktop is an Electron app. **Ctrl+P** opens the normal system print dialog and sends **HTML/layout** to whatever printer you pick (usually CUPS). That path does **not** go through printime's:

- Jinja templates (`note`, `checklist`, …)
- 48-column thermal layout
- Markdown → plain-text transform
- Preview `[CUT]` logic

So choosing your thermal printer in Ctrl+P will print Anytype's **on-screen rendering**, not the formatted receipt you got from `printime anytype fetch`.

## Recommended setup (what works well)

### 1. Install printime globally

```bash
cd ~/Documents/repos/random_projects/adhd/printime
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Add to ~/.bashrc
export PATH="$HOME/Documents/repos/random_projects/adhd/printime/.venv/bin:$PATH"
```

Verify:

```bash
printime doctor
printime anytype list
```

### 2. Keep Desktop API configured

In `.env`:

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

Anytype Desktop must be running.

### 3. Print by page title (easiest)

No object ID needed:

```bash
printime anytype print "I am 021er" --preview
printime anytype print "I am 021er"              # direct to printer
```

Search first:

```bash
printime anytype search "021er"
```

### 4. Keyboard shortcut (feels native)

**Settings → Keyboard → Custom shortcuts** (or `libinput`/desktop environment):

| Shortcut | Command |
|----------|---------|
| `Ctrl+Shift+P` | `printime anytype print "$(xclip -o)" --yes` |
| Or fixed title | `printime anytype print "I am 021er" --yes` |

Script `scripts/anytype-print-selection.sh`:

```bash
#!/bin/bash
# Bind to a hotkey — prints the page title in clipboard, or pass as arg
TITLE="${1:-$(xclip -o -selection clipboard 2>/dev/null)}"
exec printime anytype print "$TITLE" --yes
```

Copy a page title in Anytype, press the hotkey → thermal print.

## Option B: Show up in the system print dialog (advanced)

You *can* add a **CUPS virtual printer** named "Printime" so it appears in Ctrl+P, but:

- Anytype sends HTML/PDF, not markdown
- You lose template formatting (title bar, note layout, etc.)
- You only get "whatever the app rendered" squeezed onto thermal paper

Only worth it if you want **raw** printing from any app, not the template pipeline.

Rough steps (Ubuntu/CUPS):

1. Create a backend script that reads the print job and sends text to `printime print --text ...`
2. Register with `lpadmin -p Printime ...`

This is a separate project from the Anytype API workflow and is **not** recommended if you liked the template output.

## Option C: Anytype MCP in Cursor

For AI-assisted workflows, add `@anyproto/anytype-mcp` in Cursor MCP settings (same Desktop API key, port `31009`). That helps the **editor** fetch pages — not Ctrl+P inside Anytype.

## Summary

| Method | Uses templates? | Effort |
|--------|-----------------|--------|
| `printime anytype print "title"` | Yes | Low — **best** |
| Hotkey + title in clipboard | Yes | Low |
| Ctrl+P → thermal printer | No | Built-in but wrong layout |
| CUPS virtual "Printime" printer | No | High |
| `printime anytype fetch <id>` | Yes | Medium (needs ID) |

**Suggestion:** install printime on PATH, use `printime anytype print "Page Title"`, bind a global shortcut. Skip Ctrl+P for thermal — it's the wrong pipeline for what you want.
