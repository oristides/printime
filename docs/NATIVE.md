# Native integration (hotkeys, Ctrl+P, system print)

## Can I use Ctrl+P?

**Not for printime templates.**

Ctrl+P sends **PDF/HTML** through CUPS. Your thermal printer expects **ESC/POS** (receipt bytes). Even with a CUPS queue named `POS8370` and a raw driver, app printing usually fails or prints garbage.

Use printime instead:

```bash
printime print --text "Hello"
printime anytype print "Page title" --yes
printime print --qr "https://..."
```

See [QUICKSTART.md](QUICKSTART.md) for plain text and notes.

## Install globally

```bash
pipx install -e ~/Documents/repos/random_projects/printime
printime doctor
```

No venv activation or PATH hacks needed — `~/.local/bin/printime`.

After updates:

```bash
cd ~/Documents/repos/random_projects/printime && git pull
pipx reinstall printime
```

## Anytype — recommended workflow

### 1. Desktop API in `.env`

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

Anytype Desktop must be running.

### 2. Print by title

```bash
printime anytype print "I am 021er" --preview
printime anytype search "021er"
```

### 3. Keyboard shortcut

**Settings → Keyboard → Custom shortcuts:**

| Shortcut | Command |
|----------|---------|
| `Ctrl+Shift+P` | `printime anytype print "$(xclip -o -selection clipboard)" --yes` |

Or use the included script:

```bash
~/Documents/repos/random_projects/printime/scripts/anytype-print.sh "Page title"
```

## CUPS queue `POS8370`

You may see `POS8370` in the system print dialog. That does **not** mean Ctrl+P will produce good thermal output.

`printime doctor` showing `idle` is normal — printer is ready.

## Summary

| Method | Uses templates? | Works? |
|--------|-----------------|--------|
| `printime print` / `anytype print` | Yes | ✅ Best |
| Hotkey + `anytype print` | Yes | ✅ |
| Ctrl+P → POS8370 | No | ❌ PDF on receipt printer |
| `printime serve` webhook | Partial | ✅ Automation |

**Use printime commands, not Ctrl+P.**

## Cursor / agents

Agent skill: [skill/printime.md](../skill/printime.md)
