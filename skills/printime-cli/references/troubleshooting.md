# Troubleshooting

Start with:

```bash
printime doctor
printime <command> --help
```

## Common Problems

| Problem | Fix |
|---------|-----|
| `printime: command not found` | `pipx install -e ~/Documents/repos/random_projects/printime[all] --force` |
| Ticket PDF import error | `pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless` |
| Barcode/QR extraction fails | Install `libzbar0`: `sudo apt install libzbar0`. |
| `requires gkeepapi` | `pipx inject printime gkeepapi`. |
| Keep auth failed | Regenerate `GOOGLE_KEEP_MASTER_TOKEN`; verify `.env`. |
| `ANYTYPE_API_KEY not set` | Add Desktop API key to `.env` and keep Anytype Desktop running. |
| Google Calendar says URL missing | Add `GOOGLE_CALENDAR_ICS_URL` to `.env` or pass `--ics-url`. |
| Permission denied on `/dev/usb/lp*` | `sudo usermod -aG lp $USER`, then log out and back in. |
| CUPS status is `idle` | This is normal and means ready. |
| Ctrl+P prints garbage | Use Printime CLI commands, not raw CUPS printing. |
| Mermaid missing on paper | `npm install -g @mermaid-js/mermaid-cli`. |
| Unknown flag or command | Re-run with `printime <command> --help`; the CLI prints suggestions. |

## Encoding and Accents

Preview is UTF-8, but most thermal printers use legacy code pages.

Set `encoding` in `config/printer.yaml`:

```yaml
printer:
  encoding: cp860
```

Try:

| Text | Encoding |
|------|----------|
| Portuguese (`ã`, `õ`, `ç`) | `cp860`, then `cp850` |
| Spanish/French/German accents | `cp850` or `latin-1` |
| Emoji/CJK | Usually unsupported on receipt printers |

Run a physical test:

```bash
printime doctor --test-print
```

## USB Device

Find the device and IDs:

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

Printime prefers direct USB ESC/POS. If old CUPS jobs are stuck:

```bash
cancel -a POS8370
cupsdisable POS8370
```

Do not route templated output through Ctrl+P.

## Article Fetching

`printime print --url` works best with readable article pages. Paywalls, Medium, and heavily scripted pages may fail or return poor text.

Use:

```bash
printime print --url "https://example.com" --max-chars 3000 --preview
printime print --url "https://example.com" --max-chars 0 --preview
```

## Secrets

Never commit `.env`. It may contain:

- `ANYTYPE_API_KEY`
- `GOOGLE_CALENDAR_ICS_URL`
- `GOOGLE_KEEP_MASTER_TOKEN`
