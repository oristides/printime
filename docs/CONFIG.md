# Configuration

Printime reads `config/printer.yaml` and `.env` (see `.env.example`).

## Config file

`config/printer.yaml`:

```yaml
printer:
  backend: usb              # usb | cups | auto | raw (usb recommended)
  cups_queue: POS8370       # CUPS queue name (for doctor / USB release)
  device: /dev/usb/lp5
  width: 48                 # characters per line (80mm paper)
  paper_width_pixels: 576   # for centered QR/images
  profile: RP-F10-80mm      # python-escpos profile (80mm)

  usb:
    vendor_id: 0x0416
    product_id: 0x5011
    in_ep: 0x81
    out_ep: 0x01
```

`ITPP047` / `POS8370` are aliased to `RP-F10-80mm` in code — do not use `ITPP047` as profile name (not in escpos).

## Environment variables

Copy `.env.example` → `.env`:

```env
PRINTER_DEVICE=/dev/usb/lp5
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
PRINTER_CUPS_QUEUE=POS8370

GOOGLE_CALENDAR_ICS_URL=...
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo

ANYTYPE_API_URL=http://127.0.0.1:31009
ANYTYPE_API_KEY=...

SERVER_PORT=8080
```

**Never commit `.env`** — it is in `.gitignore`.

## Install / update CLI

```bash
pipx install -e ~/Documents/repos/random_projects/printime
pipx reinstall printime   # after git pull or code changes
```

## Backends

| Backend | When to use |
|---------|-------------|
| `usb` | **Default** — direct ESC/POS via python-escpos |
| `cups` | System print queue only |
| `raw` | Write bytes to `/dev/usb/lp*` |
| `auto` | Try USB → CUPS → raw |

Printime temporarily **disables** the CUPS queue during USB prints to avoid conflicts.

## Setup checklist

1. `pipx install -e ~/Documents/repos/random_projects/printime`
2. `cp .env.example .env` and fill in optional integrations
3. `ls -la /dev/usb/lp*` and `printime doctor`
4. `sudo usermod -aG lp $USER` if permission denied
5. `printime doctor --test-print`

## CUPS vs Ctrl+P

- **POS8370 in CUPS** = Linux sees the printer (`lpstat -p`)
- **`idle`** = ready, not an error
- **Ctrl+P from apps** sends PDF — thermal printer cannot render it; use `printime print` instead
- CUPS queue should use **raw** driver if you use system print at all

## Troubleshooting

### `command not found`

```bash
pipx install -e ~/Documents/repos/random_projects/printime
```

### `KeyError: 'ITPP047'` (profile)

Set `profile: RP-F10-80mm` in `config/printer.yaml`.

### Permission denied on `/dev/usb/lp5`

```bash
sudo usermod -aG lp $USER
newgrp lp   # or log out/in
```

See also `udev/80-pos8370.rules`.

### Stuck CUPS jobs

```bash
cancel -a POS8370
cupsenable POS8370
```

### Garbled characters

Thermal printers expect plain ASCII. Printime sanitizes Unicode (e.g. `•` → `*`).

### `[CUT]` on paper

Current versions: `[CUT]` is **preview only**. Update: `pipx reinstall printime`.

## Integrations

- **Google Calendar:** [GCAL.md](GCAL.md) — `GOOGLE_CALENDAR_ICS_URL`
- **Anytype:** [ANYTYPE.md](ANYTYPE.md) — Desktop API port `31009`
