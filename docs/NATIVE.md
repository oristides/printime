# Native integration (hotkeys, Ctrl+P, agents)

Printime is **CLI-first** — for terminal users, desktop hotkeys, AI agents, and apps (`printime serve`). There is no supported CUPS “Printime” network printer.

## Do not use Ctrl+P → POS8370

Ctrl+P sends **PDF/HTML** through CUPS. Your thermal printer expects **ESC/POS**. Output is usually garbage.

Use printime commands instead:

```bash
printime print --text "Hello"
printime anytype print "Page title" --preview
printime print --url 'https://…' --link-qr --preview
printime print --ticket ticket.pdf --preview
```

See [QUICKSTART.md](QUICKSTART.md) and [HOTKEYS.md](HOTKEYS.md).

## Hotkeys (recommended)

Bind shell scripts in **Settings → Keyboard → Custom shortcuts**:

| Shortcut | Script |
|----------|--------|
| `Ctrl+Shift+P` | `scripts/anytype-print.sh` |
| `Ctrl+Shift+U` | `scripts/print-url.sh` |
| `Ctrl+Shift+T` | `scripts/print-ticket.sh` |

Scripts run **`--preview`** by default. Instant print: `PRINTIME_YES=1 ./scripts/anytype-print.sh "Title"`.

Full table: [HOTKEYS.md](HOTKEYS.md).

## Install globally

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all]
printime doctor
```

After updates:

```bash
cd ~/Documents/repos/random_projects/printime && git pull
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
```

## Anytype workflow

### 1. Desktop API in `.env`

```env
ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=your-desktop-api-key
```

Anytype Desktop must be running.

### 2. Print by title

```bash
printime anytype print "Login Flow" --preview
printime anytype search "Login"
```

### 3. Hotkey

```bash
~/Documents/repos/random_projects/printime/scripts/anytype-print.sh "Page title"
```

## Apps and agents

| Integration | Use |
|-------------|-----|
| **CLI** | `printime print … --preview` |
| **HTTP** | `printime serve` → POST `/print` (see [COMMANDS.md](COMMANDS.md)) |
| **Agents** | `--preview` + `preview_capture` (see skill) |

## Summary

| Method | Templates? | Supported? |
|--------|------------|------------|
| `printime print` / integrations | Yes | ✅ Primary |
| Hotkey scripts | Yes | ✅ |
| `printime serve` | Partial | ✅ Automation |
| Ctrl+P → POS8370 | No | ❌ |

## Cursor / agents

Agent skill: [skills/printime-cli/SKILL.md](../skills/printime-cli/SKILL.md)
