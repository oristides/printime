# Install and Configuration

Use `pipx` for all installs. Do not use system `pip install`; PEP 668 blocks global package writes on this machine.

## Install

Check for `printime`, install all Python extras if missing, then run diagnostics:

```bash
(command -v printime >/dev/null && printime --version) || pipx install -e ~/Documents/repos/random_projects/printime[all] --force; printime doctor
```

Fresh full install:

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
printime --version
printime doctor
```

Minimal install without ticket PDF or Keep support:

```bash
pipx install -e ~/Documents/repos/random_projects/printime
```

## Update

After code changes or `git pull`:

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
```

If `printime` is already installed and only package metadata changed:

```bash
pipx reinstall printime
```

## Optional Extras

Ticket PDF support:

```bash
pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless
sudo apt install libzbar0
```

Google Keep support:

```bash
pipx inject printime gkeepapi
```

Mermaid diagram support:

```bash
npm install -g @mermaid-js/mermaid-cli
```

## Printer Config

Copy the generic config on first setup:

```bash
cd ~/Documents/repos/random_projects/printime
cp config/printer.example.yaml config/printer.yaml
cp .env.example .env
```

Important `config/printer.yaml` fields:

| Field | Typical value | Notes |
|-------|---------------|-------|
| `width` | `48` | 80mm paper; 58mm is usually around 32 columns. |
| `paper_width_pixels` | `576` | Used for image and QR sizing. |
| `backend` | `usb` | Recommended direct ESC/POS backend. |
| `device` | `/dev/usb/lp0` | Check with `ls -la /dev/usb/lp*`. |
| `encoding` | `cp850` or `cp860` | Use `cp860` for many Portuguese POS printers. |
| `profile` | `simple` | Use a valid python-escpos profile if needed. |

Environment overrides in `.env`:

```env
PRINTER_DEVICE=/dev/usb/lp0
PRINTER_WIDTH=48
PRINTER_BACKEND=usb
PRINTER_CUPS_QUEUE=POS8370
```

Never commit `.env`.

## Verify Setup

```bash
printime doctor
printime doctor --test-print
```

`CUPS status: idle` is good; it means the queue is ready.
