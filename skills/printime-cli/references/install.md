# Install and Configuration

**This file contains:** pipx install/update, optional extras (what each enables), `printer.yaml` / `.env` fields, verify steps.

Use `pipx` only — not system `pip install` (PEP 668 blocks global writes).

## Install

```bash
(command -v printime >/dev/null && printime --version) || \
  pipx install -e ~/Documents/repos/random_projects/printime[all] --force
printime doctor
```

Minimal (no ticket PDF or Keep):

```bash
pipx install -e ~/Documents/repos/random_projects/printime
```

## Update

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
# or metadata-only:
pipx reinstall printime
```

## Optional Extras

| Extra / package | Enables | If missing |
|-----------------|---------|------------|
| `[all]` (recommended) | Ticket PDF, Keep, common deps in one install | Various import errors per feature |
| `pymupdf`, `pyzbar`, `markitdown[pdf]`, `opencv-python-headless` | `printime ticket path.pdf` | PDF import or barcode extraction errors |
| `libzbar0` (apt) | QR/barcode decode from ticket PDFs | Extraction fails silently or errors |
| `gkeepapi` | `printime keep` | `requires gkeepapi` |
| `@mermaid-js/mermaid-cli` (npm global) | `--mermaid` and ` ```mermaid ` in markdown | Diagram missing on paper |

Inject into existing pipx app:

```bash
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
sudo apt install libzbar0
pipx inject printime gkeepapi
npm install -g @mermaid-js/mermaid-cli
```

## Printer Config

```bash
cp config/printer.example.yaml config/printer.yaml
cp .env.example .env
```

| Field | Typical value | Notes |
|-------|---------------|-------|
| `width` | `48` | 80mm; 58mm ≈ 32 columns |
| `paper_width_pixels` | `576` | Image / QR sizing |
| `backend` | `usb` | Direct ESC/POS |
| `device` | `/dev/usb/lp0` | `ls -la /dev/usb/lp*` |
| `encoding` | `cp860` | Portuguese POS; else `cp850` |
| `profile` | `simple` | python-escpos profile if needed |

`.env` overrides:

```env
PRINTER_DEVICE=/dev/usb/lp0
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
PRINTER_CUPS_QUEUE=POS8370
```

Never commit `.env`.

## Verify

```bash
printime doctor
printime doctor --test-print
```

`CUPS status: idle` means ready.
