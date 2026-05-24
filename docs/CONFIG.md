# Configuration

Printime reads settings from environment variables (`.env`) and `config/printer.yaml`.

## Config file

Default path: `config/printer.yaml`

```yaml
printer:
  backend: usb          # usb | cups | auto | raw
  cups_queue: Unknown   # CUPS queue name (if using cups)
  device: /dev/usb/lp5  # fallback raw device path
  width: 48             # characters per line (80mm paper)
  encoding: utf-8
  profile: ITPP047      # escpos profile

  usb:
    vendor_id: 0x0416
    product_id: 0x5011
    in_ep: 0x81
    out_ep: 0x01
```

## Environment variables

Create a `.env` file in the project root:

```env
PRINTER_DEVICE=/dev/usb/lp5
PRINTER_WIDTH=48
PRINTER_PROFILE=ITPP047
SERVER_PORT=8080
ANYTYPE_API_KEY=your-key-here
```

Environment variables override YAML values where supported.

## Backends

| Backend | When to use |
|---------|-------------|
| `usb` | **Recommended** — direct ESC/POS via `python-escpos` |
| `cups` | System print queue |
| `raw` | Write directly to `/dev/usb/lp*` |
| `auto` | Try USB, then CUPS, then raw |

## Setup checklist

1. **Install dependencies**

   ```bash
   pip install -e .
   ```

2. **Check device**

   ```bash
   ls -la /dev/usb/lp*
   printime doctor
   ```

3. **Permissions**

   User must be in the `lp` group:

   ```bash
   sudo adduser $USER lp
   # log out and back in
   ```

4. **Test print**

   ```bash
   printime doctor --test-print
   ```

## Troubleshooting

### `Permission denied` on `/dev/usb/lp5`

Add yourself to the `lp` group and re-login, or run `newgrp lp` in the current shell.

### CUPS queue conflicts

If a CUPS queue (e.g. `Unknown`) grabs the printer with the wrong driver, disable it before USB printing:

```bash
cancel -a Unknown
cupsdisable Unknown
```

Then retry:

```bash
printime doctor --test-print
```

### Print succeeds but nothing comes out

- Run `printime doctor` and check backend is `usb`
- Clear stuck CUPS jobs: `cancel -a`
- Verify USB IDs in `config/printer.yaml` match your printer (`lsusb`)

### Garbled characters

Printime sanitizes Unicode to ASCII for thermal printers (e.g. `•` → `*`). Use plain ASCII in note content for best results.

### `[CUT]` appeared on paper (older versions)

Current behavior: `[CUT]` is **preview only**. Paper output contains template text; the printer performs a physical cut at the end. Update with `pip install -e .` if you see `[CUT]` on paper.

## Paper width

Default width is **48 characters** for 80mm thermal paper (POS-8370). Adjust in `config/printer.yaml` if lines wrap incorrectly.

## Anytype integration

See **[ANYTYPE.md](ANYTYPE.md)** for the full setup guide.

- `ANYTYPE_API_KEY` — HTTP API requests (in your `.env`)
- Account key — `anytype auth login` only (different credential)
- `ANYTYPE_SPACE_ID` — space containing the page
- Local API URL defaults to `http://127.0.0.1:31012` (starts after login)
