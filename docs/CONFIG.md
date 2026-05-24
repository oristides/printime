# Configuration

Printime reads **`config/printer.yaml`** (your machine) and **`.env`** (secrets). The repo ships a **maintainer default** `printer.yaml` plus a generic **`config/printer.example.yaml`** — copy the example when setting up a new printer.

## First-time install (pipx)

```bash
cd ~/Documents/repos/random_projects/printime

# Full install including ticket PDF support:
pipx install -e .[tickets]

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
pipx install -e ~/Documents/repos/random_projects/printime[tickets] --force
```

**Added ticket PDF support** to an existing pipx install:

```bash
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
```

**Full reinstall with extras** (recommended after big updates):

```bash
pipx install -e ~/Documents/repos/random_projects/printime[tickets] --force
```

Optional barcode library (Linux):

```bash
sudo apt install libzbar0
```

**Never use** `pip install printime[tickets]` on the system Python (PEP 668 blocks it). Always use **pipx**.

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

## Character encoding (São Paulo, ã, ç)

- **Preview** shows real Unicode in the terminal.
- **Print** uses **`encoding: cp850`** by default (Latin/Western Europe).
- Bullets and dashes are normalized (`•` → `*`).

If characters still garble on paper, try `encoding: latin-1` or `ascii` in `printer.yaml`.

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
printime print --ticket ticket.pdf --preview --yes 2>&1 | tee /tmp/preview.txt
```

---

## Maintainer default vs yours

The committed `config/printer.yaml` is **one developer's POS-8370** setup. Your printer will differ — use `printer.example.yaml` as the template and do not assume `/dev/usb/lp5` or `POS8370`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found` | `pipx install -e .[tickets]` |
| Ticket PDF missing pymupdf | `pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless` |
| Permission denied USB | `sudo usermod -aG lp $USER` then re-login |
| `KeyError` profile | Use `simple` or a valid escpos profile name |
| CUPS `idle` | Normal — ready |
| Garbled text | Set `encoding: cp850` or `ascii` |
| Ctrl+P garbage | Use `printime print`, not CUPS PDF |

## Integrations

- [GCAL.md](GCAL.md) — Google Calendar
- [ANYTYPE.md](ANYTYPE.md) — Anytype Desktop API
