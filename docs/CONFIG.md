# Configuration

Printime reads **`config/printer.yaml`** (your machine) and **`.env`** (secrets). The repo ships a **maintainer default** `printer.yaml` plus a generic **`config/printer.example.yaml`** — copy the example when setting up a new printer.

## First-time install (pipx)

```bash
cd ~/Documents/repos/random_projects/printime

# Full install including ticket PDF and Google Keep support:
pipx install -e .[all]

# Or minimal (no PDF tickets):
pipx install -e .
```

Copy config and secrets:

```bash
cp config/printer.example.yaml config/printer.yaml   # if you don't have one yet
cp .env.example .env
printime doctor
```

## Reinstall / update after git pull

**Code only changed** (same deps):

```bash
pipx reinstall printime
# or from repo:
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
```

**Added ticket PDF support** to an existing pipx install:

```bash
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
```

**Full reinstall with extras** (recommended after big updates):

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
```

Optional barcode library (Linux):

```bash
sudo apt install libzbar0
```

**Never use** `pip install printime[all]` on the system Python (PEP 668 blocks it). Always use **pipx**.

---

## Configure your printer (agnostic)

### 1. Find your hardware

```bash
ls -la /dev/usb/lp*          # device node → printer.device
lsusb                        # ID vvpp:pppp → printer.usb.vendor_id / product_id
lpstat -p                      # queue name → printer.cups_queue (optional)
printime doctor
```

### 2. Copy the example config

```bash
cp config/printer.example.yaml config/printer.yaml
```

Edit `config/printer.yaml`:

| Field | Typical 80mm | Notes |
|-------|--------------|-------|
| `width` | `48` | Chars per line (58mm paper ≈ 32) |
| `paper_width_pixels` | `576` | 80mm @ 203dpi — QR/image centering |
| `encoding` | `cp850` | Western European (ã, ç, é). Use `ascii` if garbled |
| `backend` | `usb` | Direct ESC/POS (recommended) |
| `profile` | `simple` or `RP-F10-80mm` | python-escpos profile for your model |
| `device` | `/dev/usb/lp0` | Your device node |
| `usb.vendor_id` / `product_id` | from `lsusb` | Required for USB backend |

### 3. Environment overrides (optional)

`.env` overrides YAML:

```env
PRINTER_DEVICE=/dev/usb/lp0
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
PRINTER_CUPS_QUEUE=MyThermal
PRINTER_PROFILE=simple
```

---

## Character encoding (Portuguese, Spanish, ã, ç, ñ)

**Source files and preview are UTF-8 (Unicode).** Markdown, Anytype, and URLs can use any language in the terminal preview.

**Thermal printers rarely print raw UTF-8.** They use legacy **code pages**. Printime converts Unicode → your configured code page when sending to the printer.

Set in `config/printer.yaml`:

```yaml
printer:
  encoding: cp850    # default — Western European (ã, ç, é, ó, ñ)
  # encoding: cp860  # Portuguese IBM code page (try if cp850 garbles)
  # encoding: latin-1
  # encoding: utf-8  # only if your printer firmware supports UTF-8 ESC/POS
  # encoding: ascii  # strips accents (fallback)
```

| Language / chars | Try first |
|------------------|-----------|
| Portuguese (ã, ç, õ) | **`cp860`** for Brazilian POS printers; `cp850` for generic EU |
| Spanish (ñ, á) | `cp850` or `latin-1` |
| French, German | `cp850` |
| Emoji, CJK | not supported on most 80mm printers |

Bullets and dashes are normalized (`•` → `*`, `—` → `-`).

If **`í` and `ç` print correctly but `ã` / `õ` do not**, your printer is almost certainly on the **Portuguese code page (CP860)** while printime was sending CP850 bytes. Set:

```yaml
encoding: cp860
```

Printime now also sends `ESC t 3` to select CP860 on the printer at job start.

1. Confirm `encoding: cp850` in `config/printer.yaml`
2. Try `cp860` (Portuguese) or `latin-1`
3. Run `printime doctor --test-print` with a line like `São Paulo`
4. Reinstall after config change: `pipx install -e . --force`

---

## Backends

| Backend | When to use |
|---------|-------------|
| `usb` | **Default** — direct ESC/POS |
| `cups` | System queue only |
| `raw` | Write bytes to `/dev/usb/lp*` |
| `auto` | Try USB → CUPS → raw |

Printime temporarily **releases** the CUPS queue during USB jobs to avoid conflicts.

---

## Preview fidelity

Terminal preview simulates paper width (`width` chars), title blocks, ASCII QR (sized with `--qr-size`), and `[CUT]`.

**Agents:** verify output before printing:

```python
from printime.preview_capture import render_and_summarize, read_preview

result = render_and_summarize('ticket', context, config)
print(read_preview(result['preview']))   # digest: lines, QR rows, unicode, issues
print(result['preview'])                 # full bordered preview
```

Or CLI:

```bash
printime print --ticket ticket.pdf --preview 2>&1 | tee /tmp/preview.txt
```

---

## Maintainer default vs yours

The committed `config/printer.yaml` is **one developer's POS-8370** setup. Your printer will differ — use `printer.example.yaml` as the template and do not assume `/dev/usb/lp5` or `POS8370`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found` | `pipx install -e .[all]` |
| Ticket PDF missing pymupdf | `pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless` |
| Permission denied USB | `sudo usermod -aG lp $USER` then re-login |
| `KeyError` profile | Use `simple` or a valid escpos profile name |
| CUPS `idle` | Normal — ready |
| Garbled text | Set `encoding: cp850` or `ascii` |
| Ctrl+P garbage | Use `printime print` — see [HOTKEYS.md](HOTKEYS.md) |

## Integrations

- [GCAL.md](GCAL.md) — Google Calendar
- [ANYTYPE.md](ANYTYPE.md) — Anytype Desktop API
- [HOTKEYS.md](HOTKEYS.md) — shortcuts and app integration
