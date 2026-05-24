#!/usr/bin/env python3
"""
Printime CLI - Thermal Printer Tool
Print text, QR codes, and templates to POS-8370 thermal printer
"""

import io
import os
import sys
import time
import subprocess
import qrcode
import argparse
import json
from datetime import datetime

try:
    from escpos.printer import Usb, LP
    HAS_ESCPOS = True
except ImportError:
    HAS_ESCPOS = False
    LP = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'printer.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'printer.yaml')

    import yaml
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def _usb_id(value) -> int:
    """Parse USB vendor/product id from YAML int or hex string."""
    if isinstance(value, int):
        return value
    return int(str(value), 16)


class EscposPrinterAdapter:
    """Expose RawPrinter-like methods on python-escpos printer drivers."""

    def __init__(self, printer, width: int, backend: str = 'escpos', cups_queue: str | None = None):
        self._printer = printer
        self.width = width
        self.backend = backend
        self.cups_queue = cups_queue

    @staticmethod
    def _encode_raw(data) -> bytes:
        if isinstance(data, bytes):
            text = data.decode('utf-8')
        else:
            text = data.replace('\\r', '\r').replace('\\n', '\n')
        return text.replace('\n', '\r\n').encode('utf-8')

    def raw(self, data):
        self._printer._raw(b'\x1b\x40')
        self._printer._raw(self._encode_raw(data))

    def init(self):
        self._printer._raw(b'\x1b\x40')

    def text(self, text, align='left', bold=False, double_height=False, double_width=False):
        payload = text if text else ' '
        if align == 'center':
            payload = payload.center(self.width)
        elif align == 'right':
            payload = payload.rjust(self.width)
        self._printer.text(payload)

    def qr(self, data, size=8, center=True):
        from escpos.constants import QR_ECLEVEL_M
        self._printer.qr(data, size=size, center=center, ec=QR_ECLEVEL_M)

    def image(self, path):
        self._printer.image(path)

    def cut(self):
        self._printer.cut()

    def close(self):
        self._printer.close()


from printime.preview import sanitize_printer_text


def finish_job(printer):
    """Release printer device after a print job."""
    if getattr(printer, '_job_finished', False):
        return
    if hasattr(printer, 'close'):
        printer.close()
    if getattr(printer, 'backend', '') == 'usb' and getattr(printer, 'cups_queue', None):
        _enable_cups_queue(printer.cups_queue)
    printer._job_finished = True


def print_rendered(printer, rendered: str, cut: bool = True, png_path: str | None = None):
    """Send rendered template output to the printer and release the device."""
    backend = getattr(printer, 'backend', type(printer).__name__)
    print(f"[printime] backend={backend}", file=sys.stderr)
    text = sanitize_printer_text(rendered.replace('\r\n', '\n').replace('\r', '\n'))
    try:
        printer.raw(text)
        if png_path and hasattr(printer, 'image'):
            printer.image(png_path)
        if cut:
            printer.cut()
    except Exception as e:
        print(f"[ERROR] Print failed: {e}", file=sys.stderr)
        raise
    finally:
        finish_job(printer)


def _printer_backend(config) -> str:
    from printime.config import get_env
    return get_env('PRINTER_BACKEND', config.get('printer', {}).get('backend', 'usb')).lower()


def get_cups_queue(config) -> str | None:
    from printime.config import get_env
    queue = get_env('PRINTER_CUPS_QUEUE', config.get('printer', {}).get('cups_queue'))
    if queue:
        return queue
    if not HAS_ESCPOS or LP is None:
        return None
    try:
        lp = LP()
        for name, device in lp.printers.items():
            if any(token in device for token in ('POS80', '0416', '5011', '8370', 'ESCPO')):
                return name
    except Exception:
        return None
    return None


def _release_cups_usb(queue: str | None):
    """Cancel stuck CUPS jobs so direct USB printing can claim the device."""
    if not queue:
        return
    subprocess.run(['cancel', '-a', queue], capture_output=True)
    subprocess.run(['cupsdisable', queue], capture_output=True)


def _enable_cups_queue(queue: str | None):
    if not queue:
        return
    subprocess.run(['cupsenable', queue], capture_output=True)


def _resolve_escpos_profile(config) -> str:
    """Map configured profile name to a python-escpos capabilities profile."""
    from escpos.capabilities import get_profile_class

    aliases = {
        'ITPP047': 'RP-F10-80mm',
        'POS8370': 'RP-F10-80mm',
        'POS-8370': 'RP-F10-80mm',
    }
    name = config['printer'].get('profile') or 'RP-F10-80mm'
    name = aliases.get(name, name)
    try:
        get_profile_class(name)
        return name
    except KeyError:
        print(f"Warning: printer profile {name!r} not found, using RP-F10-80mm", file=sys.stderr)
        return 'RP-F10-80mm'


def create_printer(config):
    backend = _printer_backend(config)
    width = config['printer']['width']
    queue = get_cups_queue(config)

    if backend in ('auto', 'usb') and HAS_ESCPOS:
        try:
            if queue:
                _release_cups_usb(queue)
                time.sleep(0.3)
            usb_cfg = config['printer']['usb']
            vendor = _usb_id(usb_cfg['vendor_id'])
            product = _usb_id(usb_cfg['product_id'])
            in_ep = int(usb_cfg.get('in_ep', 0x81))
            out_ep = int(usb_cfg.get('out_ep', 0x01))
            profile = _resolve_escpos_profile(config)
            printer = Usb(
                vendor, product, in_ep=in_ep, out_ep=out_ep, timeout=5000,
                profile=profile,
            )
            return EscposPrinterAdapter(printer, width, backend='usb', cups_queue=queue)
        except Exception as e:
            if backend == 'usb':
                raise
            print(f"Warning: USB printer failed: {e}", file=sys.stderr)

    if backend in ('auto', 'cups') and queue and HAS_ESCPOS and LP is not None:
        try:
            printer = LP(queue)
            return EscposPrinterAdapter(printer, width, backend=f'cups:{queue}')
        except Exception as e:
            if backend == 'cups':
                raise
            print(f"Warning: CUPS printer failed: {e}", file=sys.stderr)

    print("Falling back to raw device...", file=sys.stderr)
    return RawPrinter(config)


class RawPrinter:
    def __init__(self, config):
        self.device = config['printer']['device']
        self.width = config['printer']['width']
        self.paper_width_pixels = int(config['printer'].get('paper_width_pixels', 576))
        self._buffer = b''
        self._fp = None

    def _write(self, data):
        self._buffer += data

    def _flush(self):
        if not self._buffer:
            return
        try:
            fd = os.open(self.device, os.O_WRONLY)
            try:
                bytes_written = os.write(fd, self._buffer)
            finally:
                os.close(fd)
            print(f"[DEBUG] Wrote {bytes_written} bytes to {self.device}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Write failed: {e}", file=sys.stderr)
            raise
        finally:
            self._buffer = b''

    def raw(self, data):
        if isinstance(data, bytes):
            text = data.decode('utf-8')
        else:
            text = data.replace('\\r', '\r').replace('\\n', '\n')
        self._write(b'\x1b\x40')
        self._write(text.replace('\n', '\r\n').encode('utf-8'))

    def close(self):
        self._flush()

    def init(self):
        self._write(b'\x1b\x40')

    def text(self, text, align='left', bold=False, double_height=False, double_width=False):
        payload = text if text else ''
        if align == 'center':
            payload = payload.center(self.width)
        elif align == 'right':
            payload = payload.rjust(self.width)
        if payload or text == '':
            self._write(payload.encode('utf-8') + b'\r\n')

    def qr(self, data, size=8, center=True):
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('1')
        w, h = img.size
        if center and w < self.paper_width_pixels:
            padded = Image.new('1', (self.paper_width_pixels, h), 1)
            padded.paste(img, ((self.paper_width_pixels - w) // 2, 0))
            img = padded
            w = self.paper_width_pixels
        rb = (w + 7) // 8
        self._write(b'\x1d\x76\x30\x00')
        self._write(bytes([rb & 0xFF, (rb >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF]))
        for y in range(h):
            row = []
            for bi in range(rb):
                byte = 0
                for bit in range(8):
                    x = bi * 8 + bit
                    if x < w and img.getpixel((x, y)) == 0:
                        byte |= 1 << (7 - bit)
                row.append(byte)
            self._write(bytes(row))
        self._write(b'\r\n')

    def image(self, path):
        from PIL import Image
        img = Image.open(path).convert('1')
        w = img.width
        h = img.height
        rb = (w + 7) // 8
        self._write(b'\x1d\x76\x30\x00')
        self._write(bytes([rb & 0xFF, (rb >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF]))
        for y in range(h):
            row = []
            for bi in range(rb):
                byte = 0
                for bit in range(8):
                    x = bi * 8 + bit
                    if x < w and img.getpixel((x, y)) == 0:
                        byte |= 1 << (7 - bit)
                row.append(byte)
            self._write(bytes(row))

    def cut(self):
        w = self.width
        self._write(b'\r\n' * 3)
        self._write(('-' * w + '\r\n').encode())
        self._write(('- ' * (w // 2) + '\r\n').encode())
        self._write(b'\r\n' * 2)
        self._write(b'\x1d\x56\x00')
        self._flush()

    def cut_marked(self):
        w = self.width
        self._write(b'\r\n' * 12)
        self._write(('-' * w + '\r\n').encode())
        self._write(('- ' * (w // 2) + '\r\n').encode())
        self._write(b'\r\n' * 6)
        self._flush()

    def cash_drawer(self):
        pass


def print_qr_test(printer, config):
    print("\n" + "=" * 50)
    print("TESTING QR CODE PRINT")
    print("=" * 50)
    print_qr_page(printer, "https://github.com/oriel", config)
    printer.cut()
    print("QR code test sent!")


def print_qr_page(printer, url: str, config, size: int = 8, title: str = 'SCAN ME', show_link: bool = False):
    """Print a large centered QR code with optional URL caption."""
    import textwrap

    width = config['printer']['width']
    divider = '=' * width

    printer.text(divider, align='center')
    printer.text(title, align='center', bold=True)
    printer.text(divider, align='center')
    printer.text('')
    printer.qr(url, size=size, center=True)
    if show_link:
        printer.text('')
        for line in textwrap.wrap(url, width=width):
            printer.text(line, align='center')
    printer.text('')


def print_text_test(printer):
    print("\n" + "=" * 50)
    print("TESTING TEXT FORMATTING")
    print("=" * 50)

    printer.text("=" * 32, align='center')
    printer.text("TEXT FORMATTING TEST", align='center', bold=True)
    printer.text("=" * 32, align='center')

    printer.text("Normal text")
    printer.text("Bold text", bold=True)
    printer.text("Center aligned", align='center')
    printer.text("Right aligned", align='right')

    printer.cut()
    print("Text test sent!")
    return True


def render_template(template_name, context, config):
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        print("Error: Jinja2 not installed. Run: pip install jinja2")
        return None

    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape()
    )

    env.filters['center'] = lambda s, w: str(s).center(int(w))
    env.filters['rjust'] = lambda s, w: str(s).rjust(int(w))
    env.filters['ljust'] = lambda s, w: str(s).ljust(int(w))
    env.filters['truncate'] = lambda s, w, end=True: str(s)[:int(w)] + ('...' if end and len(str(s)) > int(w) else '')

    template = env.get_template(f'{template_name}.j2')

    width = config['printer']['width']
    ctx = {'width': width, 'now': datetime.now()}
    ctx.update(context)

    return template.render(**ctx)


def render_for_print(template_name, context, config):
    """Render template output matching the terminal preview layout."""
    from printime.preview import render_template_for_print
    return render_template_for_print(template_name, context, config)


def load_context_file(path: str) -> dict:
    """Load template context from JSON, YAML, or Markdown file."""
    with open(path, 'r') as f:
        if path.endswith('.json'):
            return json.load(f)
        if path.endswith('.yaml') or path.endswith('.yml'):
            import yaml
            return yaml.safe_load(f)
        if path.endswith('.md'):
            from printime.services.transform import markdown_to_context
            config = load_config()
            return markdown_to_context(f.read(), path, config['printer']['width'])
        raise ValueError(f"Unsupported context file: {path} (use .json, .yaml, or .md)")


def resolve_print_input(args):
    """Map a positional input file to --md or --file and pick template from frontmatter."""
    path = getattr(args, 'input', None)
    if not path:
        return
    if args.md or args.file:
        print("Error: use either a positional file or --md/--file, not both", file=sys.stderr)
        sys.exit(2)
    if path.endswith('.md'):
        args.md = path
        ctx = load_context_file(path)
        if not args.template:
            args.template = ctx.get('template', 'note')
    elif path.endswith(('.json', '.yaml', '.yml')):
        args.file = path
        if not args.template:
            args.template = 'note'
    else:
        print(f"Error: unsupported file type: {path} (use .md, .json, or .yaml)", file=sys.stderr)
        sys.exit(2)


def cmd_print(args, config, printer):
    if args.test:
        if args.test == 'qr':
            print_qr_test(printer, config)
        elif args.test == 'text':
            print_text_test(printer)
        elif args.test == 'all':
            print_qr_test(printer, config)
            print_text_test(printer)
        else:
            print(f"Unknown test: {args.test}")
        return

    if args.text:
        printer.text(args.text, bold=args.bold, align='center' if args.center else 'left')

    if args.template:
        context = {}
        if args.file:
            context = load_context_file(args.file)
        else:
            if getattr(args, 'title', None):
                context['title'] = args.title
            if getattr(args, 'content', None):
                context['content'] = args.content
            if getattr(args, 'priority', None):
                context['priority'] = args.priority
            if getattr(args, 'tags', None):
                context['tags'] = [t.strip() for t in args.tags.split(',')]

        if args.preview:
            from printime.preview import render_template_preview, confirm
            rendered = render_template_preview(args.template, context)
            print(rendered)
            if getattr(args, 'yes', False) or confirm("Print this?"):
                result = render_for_print(args.template, context, config)
                if result:
                    print_rendered(
                        printer,
                        result,
                        cut=not getattr(args, 'no_cut', False),
                    )
                    print(f"Template '{args.template}' printed")
            else:
                print("Cancelled")
        else:
            result = render_for_print(args.template, context, config)
            if result:
                print_rendered(printer, result)
                print(f"Template '{args.template}' printed")

    if args.url:
        from printime.services.fetch_url import url_to_context

        max_chars = getattr(args, 'max_chars', 12000)
        if max_chars == 0:
            max_chars = None
        try:
            context = url_to_context(args.url, config['printer']['width'], max_chars)
        except Exception as exc:
            print(f'Error fetching URL: {exc}', file=sys.stderr)
            return
        template_name = getattr(args, 'template', None) or context.get('template', 'note')
        if context.get('truncated'):
            print('[printime] Article truncated — use --max-chars 0 for full text', file=sys.stderr)

        if args.preview:
            from printime.preview import render_template_preview, confirm
            rendered = render_template_preview(template_name, context)
            print(rendered)
            if getattr(args, 'yes', False) or confirm('Print this?'):
                result = render_for_print(template_name, context, config)
                if result:
                    print_rendered(
                        printer,
                        result,
                        cut=not getattr(args, 'no_cut', False),
                    )
                    print(f"URL printed: {args.url}")
            else:
                print('Cancelled')
        else:
            result = render_for_print(template_name, context, config)
            if result:
                print_rendered(printer, result, cut=not getattr(args, 'no_cut', False))
                print(f"URL printed: {args.url}")
        return

    if args.md:
        from printime.services.transform import markdown_to_context, latex_to_png
        with open(args.md, 'r') as f:
            content = f.read()
        context = markdown_to_context(content, args.md, config['printer']['width'])
        template_name = getattr(args, 'template', None) or context.get('template', 'note')

        png_path = None
        if 'latex' in context and context['latex']:
            png_path = latex_to_png(context['latex'], size='large')
            if png_path:
                context['image_path'] = png_path

        if args.preview:
            from printime.preview import render_template_preview, confirm
            rendered = render_template_preview(template_name, context)
            print(rendered)
            if getattr(args, 'yes', False) or confirm("Print this?"):
                try:
                    result = render_for_print(template_name, context, config)
                    if result:
                        print_rendered(
                            printer,
                            result,
                            cut=not getattr(args, 'no_cut', False),
                            png_path=png_path,
                        )
                    print("Markdown printed")
                except PermissionError:
                    print("ERROR: Permission denied. Run 'newgrp lp' first or check /dev/usb/lp5 permissions")
                except Exception as e:
                    print(f"ERROR: Print failed - {e}")
            else:
                print("Cancelled")
            return
        else:
            try:
                result = render_for_print(template_name, context, config)
                if result:
                    print_rendered(printer, result, png_path=png_path)
                print("Markdown printed")
            except PermissionError:
                print("ERROR: Permission denied. Run 'newgrp lp' first or check /dev/usb/lp5 permissions")
            except Exception as e:
                print(f"ERROR: Print failed - {e}")
            return

    if args.qr:
        qr_size = getattr(args, 'qr_size', 8)
        print_qr_page(
            printer, args.qr, config,
            size=qr_size,
            show_link=getattr(args, 'show_link', False),
        )
        if not args.no_cut:
            printer.cut()
        finish_job(printer)
        print(f"QR code printed: {args.qr}")
        return

    if args.text:
        printer.text(args.text, bold=args.bold, align='center' if args.center else 'left')
        if not args.no_cut:
            printer.cut()
        finish_job(printer)
        print("Text printed")
        return


def cmd_doctor(args, config):
    """Diagnose printer setup and run a test print."""
    from printime.config import load_env, get_env

    load_env()
    queue = get_cups_queue(config)
    backend = _printer_backend(config)

    print("Printime doctor")
    print("=" * 40)
    print(f"Configured backend : {backend}")
    print(f"Device path        : {config['printer']['device']}")
    print(f"CUPS queue         : {queue or '(not detected)'}")
    print(f"python-escpos      : {'yes' if HAS_ESCPOS else 'no'}")

    if queue:
        lpstat = subprocess.run(['lpstat', '-p', queue], capture_output=True, text=True)
        if lpstat.stdout:
            print(f"CUPS status        : {lpstat.stdout.strip()}")
        model = subprocess.run(['lpoptions', '-p', queue], capture_output=True, text=True)
        if 'Designjet' in model.stdout or 'PostScript' in model.stdout:
            print("WARNING: CUPS is using a PostScript driver for an ESC/POS printer.")
            print("         Prefer USB backend (default) or reconfigure CUPS with a raw driver.")

        jobs = subprocess.run(['lpq', '-P', queue], capture_output=True, text=True)
        if 'active' in jobs.stdout:
            print("WARNING: Stuck CUPS job detected. Run:")
            print(f"         cancel -a {queue}")
            print(f"         cupsdisable {queue}")

    if HAS_ESCPOS:
        try:
            import usb.core
            dev = usb.core.find(idVendor=0x0416, idProduct=0x5011)
            print(f"USB device         : {'found' if dev else 'NOT FOUND'}")
        except Exception as e:
            print(f"USB device         : check failed ({e})")

    if os.path.exists(config['printer']['device']):
        print(f"Device node        : present ({config['printer']['device']})")
    else:
        print(f"Device node        : MISSING ({config['printer']['device']})")

    if args.test_print:
        print("\nSending test print...")
        printer = create_printer(config)
        try:
            print_rendered(printer, "PRINTIME DOCTOR TEST\nIf you can read this, printing works.\n")
            print("Test print sent.")
        except Exception as e:
            print(f"Test print FAILED: {e}")
            return 1
    else:
        print("\nRun: printime doctor --test-print")

    return 0


def cmd_serve(args, config):
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class PrintHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == '/print':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    data = json.loads(self.rfile.read(content_length))
                else:
                    data = {}

                printer = create_printer(config)
                try:
                    if 'template' in data:
                            print_rendered(printer, render_for_print(data['template'], data.get('context', {}), config))
                            printer = None
                    else:
                        if 'qr' in data:
                            printer.qr(data['qr'])
                        if 'text' in data:
                            printer.text(data['text'], bold=data.get('bold', False))
                        if 'raw' in data:
                            printer.raw(data['raw'])
                        if data.get('cut', False):
                            printer.cut()
                finally:
                    if printer is not None:
                        finish_job(printer)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'printer': 'ready'}).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            print(f"[{self.log_date_time_string()}] {args[0]}")

    server = HTTPServer(('0.0.0.0', args.port), PrintHandler)
    print(f"Printime server running on http://0.0.0.0:{args.port}")
    print(f"POST /print with JSON: {{'text': 'hello', 'qr': 'https://...', 'cut': true}}")
    print(f"GET /health for health check")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description='Printime - Thermal Printer CLI')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 0.1.0')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    print_parser = subparsers.add_parser('print', help='Print text, QR, or template')
    print_parser.add_argument('input', nargs='?', help='Input file (.md, .json, .yaml)')
    print_parser.add_argument('--text', '-t', help='Text to print')
    print_parser.add_argument('--title', help='Title for template')
    print_parser.add_argument('--content', help='Content for template')
    print_parser.add_argument('--priority', help='Priority (HIGH, MEDIUM, LOW)')
    print_parser.add_argument('--tags', help='Tags (comma-separated)')
    print_parser.add_argument('--md', help='Print markdown file (.md)')
    print_parser.add_argument('--url', help='Fetch and print a web article (blog post, Substack, etc.)')
    print_parser.add_argument('--max-chars', type=int, default=12000,
                              help='Max article characters for --url (0 = no limit, default: 12000)')
    print_parser.add_argument('--qr', help='Print QR code with data')
    print_parser.add_argument('--qr-size', type=int, default=8,
                              help='QR module size 4-12, default 8 (larger = bigger code)')
    print_parser.add_argument('--show-link', action='store_true',
                              help='Print the URL text below the QR code')
    print_parser.add_argument('--template', help='Template name to use')
    print_parser.add_argument('--file', '-f', help='Context file (.md, .json, or .yaml)')
    print_parser.add_argument('--bold', action='store_true', help='Bold text')
    print_parser.add_argument('--center', action='store_true', help='Center align')
    print_parser.add_argument('--double-height', action='store_true', help='Double height text')
    print_parser.add_argument('--preview', '-p', action='store_true', help='Preview before printing')
    print_parser.add_argument('--no-cut', action='store_true', help='Do not cut paper')
    print_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    print_parser.add_argument('--test', choices=['qr', 'text', 'all'], help='Run test print')

    serve_parser = subparsers.add_parser('serve', help='Start HTTP server')
    serve_parser.add_argument('--port', '-p', type=int, default=8080, help='Port (default: 8080)')

    list_parser = subparsers.add_parser('list', help='List available templates')

    doctor_parser = subparsers.add_parser('doctor', help='Diagnose printer setup')
    doctor_parser.add_argument('--test-print', action='store_true', help='Send a test page')

    preview_parser = subparsers.add_parser('preview', help='Preview what will be printed')
    preview_parser.add_argument('--text', '-t', help='Text to preview')
    preview_parser.add_argument('--template', help='Template to preview')
    preview_parser.add_argument('--title', help='Title for template preview')
    preview_parser.add_argument('--content', help='Content for template preview')
    preview_parser.add_argument('--file', '-f', help='Context file (.md, .json, or .yaml)')
    preview_parser.add_argument('--no-cut', action='store_true', help='Do not cut paper after printing')
    preview_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    transform_parser = subparsers.add_parser('transform', help='Transform file to print format')
    transform_parser.add_argument('input', nargs='?', help='Input file path (.md, .tex, .txt)')
    transform_parser.add_argument('--type', '-t', choices=['context', 'text', 'image'],
                                   help='Output type (auto-detected from extension)')
    transform_parser.add_argument('--template', help='Template to wrap result in')
    transform_parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    transform_parser.add_argument('--url', help='Fetch a web article instead of a local file')
    transform_parser.add_argument('--max-chars', type=int, default=12000,
                                  help='Max article characters for --url (0 = no limit)')
    transform_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    transform_parser.add_argument('--preview', '-p', action='store_true', help='Preview before print')

    anytype_parser = subparsers.add_parser('anytype', help='Anytype integration')
    anytype_sub = anytype_parser.add_subparsers(dest='anytype_cmd')
    anytype_list = anytype_sub.add_parser('list', help='List Anytype spaces')
    anytype_join = anytype_sub.add_parser('join', help='Join a space via invite link')
    anytype_join.add_argument('invite_link', nargs='?', help='Invite link from Anytype Desktop')
    anytype_join.add_argument('--file', '-f', help='File with one invite link per line')
    anytype_fetch = anytype_sub.add_parser('fetch', help='Fetch a page')
    anytype_fetch.add_argument('page_id', help='Page ID to fetch')
    anytype_fetch.add_argument('--space', '-s', help='Space ID (optional; searches all joined spaces by default)')
    anytype_fetch.add_argument('--template', '-t', help='Template to use')
    anytype_fetch.add_argument('--preview', '-p', action='store_true', help='Preview before print')
    anytype_search = anytype_sub.add_parser('search', help='Search pages across all spaces')
    anytype_search.add_argument('query', help='Search text')
    anytype_print = anytype_sub.add_parser('print', help='Search by title and print')
    anytype_print.add_argument('query', help='Page title or search text')
    anytype_print.add_argument('--template', '-t', help='Template to use')
    anytype_print.add_argument('--preview', '-p', action='store_true', help='Preview before print')
    anytype_print.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    agenda_parser = subparsers.add_parser('agenda', help="Print Google Calendar agenda")
    agenda_parser.add_argument('--preview', '-p', action='store_true', help='Preview before printing')
    agenda_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    agenda_parser.add_argument('--days', type=int, default=1, help='Number of days to include (default: 1)')
    agenda_parser.add_argument('--next-week', action='store_true', help='Print Mon–Sun of the upcoming week')
    agenda_parser.add_argument('--ics-url', help='Override GOOGLE_CALENDAR_ICS_URL from .env')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    config = load_config()

    if args.command == 'print':
        resolve_print_input(args)
        printer = create_printer(config)
        try:
            cmd_print(args, config, printer)
        finally:
            finish_job(printer)
    elif args.command == 'serve':
        cmd_serve(args, config)
    elif args.command == 'doctor':
        return cmd_doctor(args, config)
    elif args.command == 'list':
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        if not os.path.exists(template_dir):
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

        if os.path.exists(template_dir):
            import yaml
            for f in os.listdir(template_dir):
                if f.endswith('.yaml'):
                    name = f[:-5]
                    path = os.path.join(template_dir, f)
                    with open(path, 'r') as yf:
                        data = yaml.safe_load(yf)
                    desc = data.get('description', 'No description')
                    print(f"  {name:<15} - {desc}")
                elif f.endswith('.j2'):
                    name = f[:-3]
                    yaml_path = os.path.join(template_dir, name + '.yaml')
                    if os.path.exists(yaml_path):
                        pass
                    else:
                        print(f"  {name:<15} - (no metadata)")

    elif args.command == 'preview':
        from printime.preview import render_template_preview, confirm
        context = {}
        if args.file:
            try:
                context = load_context_file(args.file)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

        template_name = args.template or context.get('template', 'note')
        if not context:
            if getattr(args, 'title', None):
                context['title'] = args.title
            if getattr(args, 'content', None):
                context['content'] = args.content
        no_cut = getattr(args, 'no_cut', False)
        auto_yes = getattr(args, 'yes', False)

        if args.text:
            from printime.preview import PaperPreview
            preview = PaperPreview()
            preview._add_line(args.text)
            preview.footer()
            print(preview.render())
            if auto_yes or confirm("Print this?"):
                printer = create_printer(config)
                try:
                    printer.text(args.text, bold=getattr(args, 'bold', False), align='center' if getattr(args, 'center', False) else 'left')
                    if not no_cut:
                        printer.cut()
                finally:
                    finish_job(printer)
                print("Printed successfully")
        elif args.file or context or getattr(args, 'title', None) or getattr(args, 'content', None):
            rendered = render_template_preview(template_name, context)
            print(rendered)
            if auto_yes or confirm("Print this?"):
                try:
                    printer = create_printer(config)
                    result = render_for_print(template_name, context, config)
                    if result:
                        print_rendered(printer, result, cut=not no_cut)
                        print("Printed successfully")
                except Exception as e:
                    print(f"Print failed: {e}", file=sys.stderr)
                    return 1
        else:
            print("Use --text or --template with --file")

    elif args.command == 'transform':
        from printime.services.transform import transform_file, markdown_to_context

        if args.url:
            from printime.services.fetch_url import url_to_context

            max_chars = getattr(args, 'max_chars', 12000)
            if max_chars == 0:
                max_chars = None
            try:
                result = {'type': 'context', 'content': url_to_context(args.url, config['printer']['width'], max_chars)}
            except Exception as exc:
                print(f'Error fetching URL: {exc}', file=sys.stderr)
                return 1
        elif args.input:
            result = transform_file(args.input, args.type)
        else:
            print('Error: provide input file or --url', file=sys.stderr)
            return 1

        if result['type'] == 'error':
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1

        if result['type'] == 'context':
            output = json.dumps(result['content'], indent=2)
        elif result['type'] == 'image':
            print(f"Image generated: {result.get('image_path', 'unknown')}")
            output = f"Image: {result.get('image_path', 'unknown')}"
        else:
            output = result.get('content', '')

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Written to {args.output}")
        elif not (args.template and getattr(args, 'preview', False)):
            print(output)

        # If template specified, render with template
        if args.template and result['type'] == 'context':
            from printime.preview import render_template_preview, confirm
            template_name = args.template or result['content'].get('template', 'note')
            rendered = render_template_preview(template_name, result['content'])
            print(rendered)
            auto_yes = getattr(args, 'yes', False)
            if auto_yes or getattr(args, 'preview', False) and confirm("Print this?"):
                try:
                    printer = create_printer(config)
                    tmpl_result = render_for_print(template_name, result['content'], config)
                    if tmpl_result:
                        print_rendered(
                            printer,
                            tmpl_result,
                            cut=not getattr(args, 'no_cut', False),
                        )
                        print("Printed successfully")
                except Exception as e:
                    print(f"Print failed: {e}", file=sys.stderr)
                    return 1
            elif getattr(args, 'preview', False):
                print("Cancelled")

    elif args.command == 'anytype':
        from printime.services.anytype import (
            print_page, print_page_by_query, join_space, join_spaces_from_file,
            global_search, list_spaces,
        )
        if args.anytype_cmd == 'fetch':
            print_page(args.page_id, template=args.template, space_id=getattr(args, 'space', None),
                       preview=args.preview, config=config)
        elif args.anytype_cmd == 'print':
            ok = print_page_by_query(
                args.query,
                template=getattr(args, 'template', None),
                preview=getattr(args, 'preview', False),
                config=config,
            )
            if not ok:
                return 1
        elif args.anytype_cmd == 'search':
            hits = global_search(args.query)
            if not hits:
                print(f"No results for: {args.query!r}")
                return 1
            for obj in hits:
                space = obj.get('space_id', '')[:20]
                print(f"  {obj.get('name')!r:<40} {obj.get('id')}  ({space}...)")
        elif args.anytype_cmd == 'join':
            if getattr(args, 'file', None):
                join_spaces_from_file(args.file)
            elif args.invite_link:
                join_space(args.invite_link)
                from printime.services.anytype import list_spaces
                list_spaces()
            else:
                print("Usage: printime anytype join '<invite-link>'", file=sys.stderr)
                print("   or: printime anytype join --file examples/anytype-invites.txt", file=sys.stderr)
                return 1
        elif args.anytype_cmd == 'list':
            list_spaces()

    elif args.command == 'agenda':
        from datetime import date

        from printime.services.gcal import next_week_start, print_agenda

        start_day = next_week_start() if getattr(args, 'next_week', False) else None
        days = 7 if getattr(args, 'next_week', False) else getattr(args, 'days', 1)

        ok = print_agenda(
            preview=getattr(args, 'preview', False),
            yes=getattr(args, 'yes', False),
            days=days,
            ics_url=getattr(args, 'ics_url', None),
            start_day=start_day,
            config=config,
        )
        if not ok:
            return 1


if __name__ == '__main__':
    main()