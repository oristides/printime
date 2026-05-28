# Troubleshooting

**This file contains:** problem/fix table, encoding guidance, USB device setup, CUPS conflicts, article-fetch limits.

**Start here:** `printime doctor` — then `printime <command> --help` for flag typos.

```bash
printime doctor
printime doctor --test-print
```

## Common Problems

| Problem | Fix |
|---------|-----|
| `printime: command not found` | `pipx install -e ~/Documents/repos/random_projects/printime[all] --force` |
| Ticket PDF import error | `pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless` + `sudo apt install libzbar0` |
| Barcode/QR extraction fails | `sudo apt install libzbar0` |
| `requires gkeepapi` | `pipx inject printime gkeepapi` |
| Keep auth failed | Regenerate `GOOGLE_KEEP_MASTER_TOKEN`; verify `.env` |
| `ANYTYPE_API_KEY not set` | Desktop API key in `.env`; Anytype Desktop running |
| Google Calendar URL missing | `GOOGLE_CALENDAR_ICS_URL` in `.env` or `--ics-url` |
| Permission denied on `/dev/usb/lp*` | `sudo usermod -aG lp $USER`, re-login |
| CUPS status `idle` | Normal — queue ready |
| Ctrl+P prints garbage | Use `printime print`, not raw CUPS for templated jobs |
| Mermaid missing on paper | `npm install -g @mermaid-js/mermaid-cli` |
| Unknown flag or command | `printime <command> --help` (suggestions printed) |

## Encoding and Accents

Preview is UTF-8; paper uses legacy code pages from `config/printer.yaml`:

```yaml
printer:
  encoding: cp860
```

| Text | Use |
|------|-----|
| Portuguese (`ã`, `õ`, `ç`) | **`cp860`** (default for many Brazilian POS printers). Use `cp850` only if `cp860` still garbles. |
| Spanish / French / German | `cp850` or `latin-1` |
| Emoji / CJK | Usually unsupported |

Verify on paper: `printime doctor --test-print`

## USB Device

Never commit `.env` — it may hold `ANYTYPE_API_KEY`, `GOOGLE_CALENDAR_ICS_URL`, and `GOOGLE_KEEP_MASTER_TOKEN` (full account access).

Find device:

```bash
ls -la /dev/usb/lp*
lsusb
```

Set in `config/printer.yaml` or `.env`:

```env
PRINTER_DEVICE=/dev/usb/lp0
PRINTER_BACKEND=usb
```

## CUPS Conflicts

Printime prefers direct USB ESC/POS. Stuck jobs:

```bash
cancel -a POS8370
cupsdisable POS8370
```

Do not route templated output through Ctrl+P.

## Article Fetching

`printime print --url` works on readable article HTML. Paywalls, Medium, and heavy JS often fail. Use `--max-chars 3000` or `--max-chars 0`.
