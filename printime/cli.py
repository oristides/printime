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

    def __init__(
        self,
        printer,
        width: int,
        backend: str = 'escpos',
        cups_queue: str | None = None,
        paper_width_pixels: int = 576,
        encoding: str = 'cp850',
    ):
        self._printer = printer
        self.width = width
        self.paper_width_pixels = paper_width_pixels
        self.encoding = encoding
        self.backend = backend
        self.cups_queue = cups_queue

    def _encode_payload(self, text: str) -> bytes:
        from printime.text_encoding import encode_for_printer, resolve_printer_encoding

        return encode_for_printer(text, resolve_printer_encoding(self.encoding))

    def _apply_code_page(self) -> None:
        from printime.text_encoding import escpos_select_code_page

        cmd = escpos_select_code_page(self.encoding)
        if cmd:
            self._printer._raw(cmd)

    def raw(self, data):
        if isinstance(data, bytes):
            text = data.decode('utf-8')
        else:
            text = data.replace('\\r', '\r').replace('\\n', '\n')
        self._printer._raw(b'\x1b\x40')
        self._apply_code_page()
        self._printer._raw(self._encode_payload(text.replace('\n', '\r\n')))

    def init(self):
        self._printer._raw(b'\x1b\x40')
        self._apply_code_page()

    def text(self, text, align='left', bold=False, double_height=False, double_width=False):
        payload = text if text else ' '
        cols = self.width // 2 if double_width else self.width
        if align == 'center':
            payload = payload.center(cols)
        elif align == 'right':
            payload = payload.rjust(cols)
        align_map = {'left': 'left', 'center': 'center', 'right': 'right'}
        self._printer.set(
            align=align_map.get(align, 'left'),
            bold=bold,
            double_height=double_height,
            double_width=double_width,
        )
        self._printer._raw(self._encode_payload(payload) + b'\r\n')
        self._printer.set(bold=False, double_height=False, double_width=False, align='left')
        self._printer._raw(b'\x1d!\x00')
        self._printer._raw(b'\r\n')
        if double_height:
            self._printer._raw(b'\r\n')

    def qr(self, data, size=8, center=True, align=None):
        from escpos.constants import QR_ECLEVEL_M
        if align is None:
            align = 'center' if center else 'left'
        if align == 'right':
            from printime.preview_qr import make_aligned_qr_image
            img = make_aligned_qr_image(
                data,
                qr_size=size,
                paper_width_pixels=self.paper_width_pixels,
                align='right',
            )
            if img is not None:
                self.image_from_pil(img)
                return
        self._printer.qr(data, size=size, center=(align == 'center'), ec=QR_ECLEVEL_M)

    def image_from_pil(self, img):
        w, h = img.size
        rb = (w + 7) // 8
        self._printer._raw(b'\x1d\x76\x30\x00')
        self._printer._raw(bytes([rb & 0xFF, (rb >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF]))
        for y in range(h):
            row = []
            for bi in range(rb):
                byte = 0
                for bit in range(8):
                    x = bi * 8 + bit
                    if x < w and img.getpixel((x, y)) == 0:
                        byte |= 1 << (7 - bit)
                row.append(byte)
            self._printer._raw(bytes(row))
        self._printer._raw(b'\r\n')

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
    if hasattr(printer, '_code_page_set'):
        printer._code_page_set = False
    if hasattr(printer, 'close'):
        printer.close()
    if getattr(printer, 'backend', '') == 'usb' and getattr(printer, 'cups_queue', None):
        _enable_cups_queue(printer.cups_queue)
    printer._job_finished = True


def _reset_text_style(printer) -> None:
    """Force normal text mode so heading sizes do not bleed into body lines."""
    if hasattr(printer, '_write_style'):
        printer._write_style(reset=True)
        return
    raw = getattr(printer, '_printer', printer)
    if hasattr(raw, '_raw'):
        raw._raw(b'\x1ba\x00\x1bE\x00\x1d!\x00')
    elif hasattr(printer, 'set'):
        try:
            printer.set(bold=False, double_height=False, double_width=False, align='left')
        except Exception:
            pass


def _feed_line(printer, count: int = 1) -> None:
    """Advance the paper by one or more lines."""
    for _ in range(count):
        if hasattr(printer, '_write'):
            printer._write(b'\r\n')
        elif hasattr(getattr(printer, '_printer', None), '_raw'):
            printer._printer._raw(b'\r\n')
        else:
            printer.text('', align='left')


def _ensure_code_page(printer) -> None:
    """Select printer code page once per job (ESC t n after ESC @)."""
    if getattr(printer, '_code_page_set', False):
        return
    if hasattr(printer, 'init'):
        printer.init()
    printer._code_page_set = True  # type: ignore[attr-defined]


def print_styled_lines(printer, lines, width: int = 48) -> None:
    """Send styled lines using ESC/POS text modes."""
    from printime.styled import PrintLine

    _ensure_code_page(printer)

    for line in lines:
        if not isinstance(line, PrintLine):
            continue
        _reset_text_style(printer)
        if not line.text:
            _feed_line(printer)
            continue
        printer.text(
            line.text,
            align=line.align,
            bold=line.bold,
            double_height=line.double_height,
            double_width=line.double_width,
        )
        _reset_text_style(printer)
        if line.double_height:
            _feed_line(printer)


def _printer_encoding(printer, default: str = 'cp850') -> str:
    return getattr(printer, 'encoding', default)


def _print_plain_block(printer, lines: list[str]) -> None:
    """Print plain lines with guaranteed line breaks on every backend."""
    from printime.text_encoding import encode_for_printer, resolve_printer_encoding, sanitize_printer_text

    enc = resolve_printer_encoding(_printer_encoding(printer))
    block = sanitize_printer_text('\n'.join(lines) + '\n', encoding=enc)
    _reset_text_style(printer)
    if hasattr(printer, '_write'):
        printer._write_style(align='left')
        printer._write(encode_for_printer(block.replace('\n', '\r\n'), enc))
        printer._write_style(reset=True)
    elif hasattr(printer, 'raw'):
        printer.raw(block)
    else:
        for line in lines:
            printer.text(line, align='left')
            _feed_line(printer)


def _print_title_block(printer, title: str, width: int, caption: str | None = None) -> None:
    lines = ['=' * width, title.upper()]
    if caption:
        lines.append(caption)
    lines.append('=' * width)
    _print_plain_block(printer, lines)
    _feed_line(printer)


def print_segments(
    printer,
    config: dict,
    template_name: str,
    context: dict,
    *,
    cut: bool = True,
) -> None:
    """Print markdown segments in document order (text, checklist, diagram, QR)."""
    from printime.services.diagram import mermaid_to_png

    _ensure_code_page(printer)
    width = config['printer']['width']
    pixels = int(config.get('printer', {}).get('paper_width_pixels', 576))
    segments = context.get('segments') or []
    caption = context.get('caption')

    title = context.get('title')
    if title and template_name in ('document', 'checklist', 'note', 'ticket'):
        _print_title_block(printer, title, width, caption=caption)

    for seg in segments:
        seg_type = seg.get('type')
        if seg_type == 'styled':
            print_styled_lines(printer, seg.get('lines') or [])
        elif seg_type == 'items':
            _feed_line(printer)
            for item in seg.get('items') or []:
                mark = 'X' if item.get('checked') else ' '
                _reset_text_style(printer)
                printer.text(f"[{mark}] {item.get('text', '')}", align='left')
                _feed_line(printer)
        elif seg_type == 'mermaid':
            png_path = mermaid_to_png(seg.get('source', ''), width=pixels)
            if png_path and hasattr(printer, 'image'):
                printer.image(png_path)
                _feed_line(printer)
        elif seg_type == 'ascii_art':
            align = seg.get('align', 'left')
            lines = seg.get('lines') or []
            if lines:
                _reset_text_style(printer)
                # One print call keeps FIGlet rows tight, like piping API output
                # through `printime print --text`. Lines are already aligned.
                printer.text('\n'.join(lines), align='left')
        elif seg_type == 'barcode':
            data = seg.get('data', '')
            sym = seg.get('symbology', 'barcode')
            if data and hasattr(printer, 'qr'):
                printer.text(sym.upper(), align='center', bold=True)
                printer.qr(data, size=seg.get('qr_size', 8), center=True)
                _feed_line(printer)
        elif seg_type == 'code_image':
            path = seg.get('image_path')
            if path and os.path.isfile(path) and hasattr(printer, 'image'):
                from printime.services.diagram import prepare_image_for_print
                prepared = prepare_image_for_print(path, max_width=pixels)
                printer.image(prepared)
                _feed_line(printer)
        elif seg_type == 'qr':
            data = seg.get('data', '')
            if not data or not hasattr(printer, 'qr'):
                continue
            size = seg.get(
                'qr_size',
                int(config.get('printer', {}).get('qr_size', 8)),
            )
            center = bool(seg.get('center', False))
            printer.qr(data, size=size, center=center)
            if seg.get('show_link'):
                import textwrap

                align = 'center' if center else 'left'
                printer.text('')
                for line in textwrap.wrap(data, width=width):
                    printer.text(line, align=align)
            printer.text('')

    if cut:
        printer.cut()


def _extract_styled_lines(context: dict) -> tuple[dict, list | None, str | None]:
    """Remove styled line lists from context; return field name for marker injection."""
    ctx = dict(context)
    for key, field in (
        ('content_lines', 'content'),
        ('description_lines', 'description'),
        ('caption_lines', 'caption'),
        ('body_lines', 'body'),
    ):
        if key in ctx:
            return ctx, ctx.pop(key), field
    return ctx, None, None


def print_rendered(
    printer,
    rendered: str,
    cut: bool = True,
    png_path: str | None = None,
    styled_lines: list | None = None,
):
    """Send rendered template output to the printer and release the device."""
    from printime.styled import STYLED_CONTENT_MARKER

    backend = getattr(printer, 'backend', type(printer).__name__)
    print(f"[printime] backend={backend}", file=sys.stderr)
    enc = _printer_encoding(printer)
    text = sanitize_printer_text(rendered.replace('\r\n', '\n').replace('\r', '\n'), encoding=enc)
    try:
        _ensure_code_page(printer)
        if styled_lines and STYLED_CONTENT_MARKER.strip() in text:
            before, _, after = text.partition(STYLED_CONTENT_MARKER.strip())
            if before:
                printer.raw(before)
            print_styled_lines(printer, styled_lines)
            if after.lstrip('\n'):
                printer.raw(after)
        else:
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


def print_image_page(
    printer,
    config,
    image_path: str,
    *,
    title: str | None = None,
    caption: str | None = None,
    cut: bool = True,
) -> None:
    """Print a raster image with optional title and caption."""
    from printime.services.diagram import prepare_image_for_print

    width = config['printer']['width']
    max_px = int(config['printer'].get('paper_width_pixels', 576))
    prepared = prepare_image_for_print(image_path, max_width=max_px)
    try:
        if title:
            divider = '=' * width
            printer.text(divider, align='center')
            printer.text(title, align='center', bold=True)
            printer.text(divider, align='center')
            printer.text('')
        printer.image(prepared)
        if caption:
            printer.text('')
            printer.text(caption, align='center')
        if cut:
            printer.cut()
    finally:
        finish_job(printer)


def _resolve_context_image(context: dict, config) -> str | None:
    """Render mermaid/LaTeX/frontmatter image refs to a PNG path."""
    from printime.services.diagram import mermaid_to_png, prepare_image_for_print
    from printime.services.transform import latex_to_png

    pixels = int(config['printer'].get('paper_width_pixels', 576))
    if context.get('mermaid'):
        return mermaid_to_png(context['mermaid'], width=pixels)
    image_ref = context.get('image') or context.get('image_path')
    if image_ref and os.path.isfile(str(image_ref)):
        return prepare_image_for_print(str(image_ref), max_width=pixels)
    if context.get('latex'):
        return latex_to_png(context['latex'], size='large')
    return None


def _print_image_job(printer, config, image_path: str, args, *, label: str = 'Image') -> None:
    from printime.preview import render_image_preview

    width = config['printer']['width']
    title = getattr(args, 'title', None)
    caption = getattr(args, 'content', None)
    if args.preview:
        print(render_image_preview(image_path, title=title, caption=caption, width=width))
        if not getattr(args, 'yes', False):
            print('Preview only. Add --yes to print.')
            return
    print_image_page(
        printer, config, image_path,
        title=title, caption=caption, cut=not args.no_cut,
    )
    print(f'{label} printed')


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
            return EscposPrinterAdapter(
                printer, width, backend='usb', cups_queue=queue,
                paper_width_pixels=int(config['printer'].get('paper_width_pixels', 576)),
                encoding=config['printer'].get('encoding', 'cp850'),
            )
        except Exception as e:
            if backend == 'usb':
                raise
            print(f"Warning: USB printer failed: {e}", file=sys.stderr)

    if backend in ('auto', 'cups') and queue and HAS_ESCPOS and LP is not None:
        try:
            printer = LP(queue)
            return EscposPrinterAdapter(
                printer, width, backend=f'cups:{queue}',
                paper_width_pixels=int(config['printer'].get('paper_width_pixels', 576)),
                encoding=config['printer'].get('encoding', 'cp850'),
            )
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
        self.encoding = config['printer'].get('encoding', 'cp850')
        self._buffer = b''
        self._fp = None

    def _encode_text(self, text: str) -> bytes:
        from printime.text_encoding import encode_for_printer
        enc = self.encoding if self.encoding in ('cp850', 'cp860', 'latin-1', 'ascii', 'utf-8') else 'cp850'
        return encode_for_printer(text, enc)

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
        from printime.text_encoding import escpos_select_code_page

        cmd = escpos_select_code_page(self.encoding)
        if cmd:
            self._write(cmd)
        self._write(self._encode_text(text.replace('\n', '\r\n')))

    def close(self):
        self._flush()

    def init(self):
        self._write(b'\x1b\x40')
        from printime.text_encoding import escpos_select_code_page

        cmd = escpos_select_code_page(self.encoding)
        if cmd:
            self._write(cmd)

    def text(self, text, align='left', bold=False, double_height=False, double_width=False):
        payload = text if text else ''
        cols = self.width // 2 if double_width else self.width
        if align == 'center':
            payload = payload.center(cols)
        elif align == 'right':
            payload = payload.rjust(cols)
        self._write_style(align=align, bold=bold, double_height=double_height, double_width=double_width)
        if payload or text == '':
            self._write(self._encode_text(payload) + b'\r\n')
        if double_height:
            self._write(b'\r\n')
        self._write_style(reset=True)

    def _write_style(
        self,
        *,
        align: str = 'left',
        bold: bool = False,
        double_height: bool = False,
        double_width: bool = False,
        reset: bool = False,
    ):
        if reset:
            self._write(b'\x1ba\x00')  # align left
            self._write(b'\x1bE\x00')  # bold off
            self._write(b'\x1d!\x00')  # normal size
            return
        align_bytes = {'left': b'\x1ba\x00', 'center': b'\x1ba\x01', 'right': b'\x1ba\x02'}
        self._write(align_bytes.get(align, b'\x1ba\x00'))
        self._write(b'\x1bE\x01' if bold else b'\x1bE\x00')
        size = 0
        if double_height:
            size |= 0x01
        if double_width:
            size |= 0x10
        self._write(bytes([0x1d, 0x21, size]))

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
    ctx = {'width': width, 'now': datetime.now().strftime('%Y-%m-%d %H:%M')}
    ctx.update(context)

    return template.render(**ctx)


def render_for_print(template_name, context, config):
    """Render template output matching the terminal preview layout."""
    from printime.preview import render_template_for_print
    return render_template_for_print(template_name, context, config)


def resolve_input_path(path: str) -> str:
    """Resolve a user file path from cwd or the printime install directory."""
    if os.path.isfile(path):
        return os.path.abspath(path)

    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_examples = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'examples')
    candidates = [
        os.path.abspath(path),
        os.path.join(pkg_root, path),
        os.path.join(pkg_root, 'examples', os.path.basename(path)),
        os.path.join(bundled_examples, os.path.basename(path)),
    ]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError(path)


def load_context_file(path: str) -> dict:
    """Load template context from JSON, YAML, or Markdown file."""
    path = resolve_input_path(path)
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
    try:
        path = resolve_input_path(path)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"Hint: try full path, e.g. {pkg_root}/examples/{os.path.basename(path)}", file=sys.stderr)
        sys.exit(2)
    if path.endswith('.md'):
        args.md = path
        ctx = load_context_file(path)
        if not args.template:
            args.template = ctx.get('template', 'note')
    elif path.endswith('.pdf'):
        args.ticket = path
    elif path.endswith(('.json', '.yaml', '.yml')):
        args.file = path
        if not args.template:
            args.template = 'note'
    else:
        print(f"Error: unsupported file type: {path} (use .md, .pdf, .json, or .yaml)", file=sys.stderr)
        sys.exit(2)


def _resolve_print_file_args(args) -> None:
    """Resolve --md / --file paths the same way as positional inputs."""
    for attr in ('md', 'file'):
        path = getattr(args, attr, None)
        if not path:
            continue
        try:
            setattr(args, attr, resolve_input_path(path))
        except FileNotFoundError:
            print(f"Error: file not found: {path}", file=sys.stderr)
            pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            print(f"Hint: try full path, e.g. {pkg_root}/examples/{os.path.basename(path)}", file=sys.stderr)
            sys.exit(2)


def _uses_segment_print(context: dict, template_name: str) -> bool:
    from printime.services.markdown_blocks import should_use_segment_print

    return should_use_segment_print(context.get('segments') or [], template_name)


def _print_template(
    printer,
    config,
    template_name: str,
    context: dict,
    *,
    preview: bool = False,
    yes: bool = False,
    no_cut: bool = False,
    png_path: str | None = None,
    label: str = 'Template',
) -> None:
    from printime.preview import render_template_preview
    from printime.styled import STYLED_CONTENT_MARKER

    if _uses_segment_print(context, template_name):
        ctx = dict(context)
        ctx.setdefault('paper_width_pixels', int(config['printer'].get('paper_width_pixels', 576)))
        if preview:
            rendered = render_template_preview(template_name, ctx)
            print(rendered)
            if not yes:
                print('Preview only. Add --yes to print.')
                return
        print_segments(
            printer, config, template_name, ctx, cut=not no_cut,
        )
        finish_job(printer)
        print(f"{label} '{template_name}' printed")
        return

    render_ctx, styled_lines, styled_field = _extract_styled_lines(context)

    if preview:
        rendered = render_template_preview(
            template_name,
            render_ctx,
            styled_lines=styled_lines,
            styled_field=styled_field,
        )
        print(rendered)
        if not yes:
            print('Preview only. Add --yes to print.')
            return

    print_ctx = dict(render_ctx)
    if styled_lines and styled_field:
        print_ctx[styled_field] = STYLED_CONTENT_MARKER.strip()

    result = render_for_print(template_name, print_ctx, config)
    if result:
        print_rendered(
            printer, result, cut=not no_cut, png_path=png_path, styled_lines=styled_lines,
        )
        print(f"{label} '{template_name}' printed")


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

    if getattr(args, 'image', None):
        if not os.path.isfile(args.image):
            print(f'Error: image not found: {args.image}', file=sys.stderr)
            return
        _print_image_job(printer, config, args.image, args, label='Image')
        return

    if getattr(args, 'mermaid', None):
        from printime.services.diagram import mermaid_to_png

        pixels = int(config['printer'].get('paper_width_pixels', 576))
        png_path = mermaid_to_png(args.mermaid, width=pixels)
        if not png_path:
            print('Error: mermaid render failed (install mermaid-cli)', file=sys.stderr)
            return
        _print_image_job(printer, config, png_path, args, label='Diagram')
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

    if getattr(args, 'ticket', None):
        from printime.services.tickets import pdf_to_ticket_context

        if not os.path.isfile(args.ticket):
            print(f'Error: ticket PDF not found: {args.ticket}', file=sys.stderr)
            return
        try:
            context = pdf_to_ticket_context(args.ticket, config['printer']['width'])
        except ImportError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return
        _print_template(
            printer, config, 'ticket', context,
            preview=args.preview, yes=getattr(args, 'yes', False),
            no_cut=getattr(args, 'no_cut', False), label='Ticket',
        )
        if not args.preview:
            print(f'Ticket printed: {args.ticket}')
        return

    if args.url:
        from printime.services.fetch_url import url_to_context

        max_chars = getattr(args, 'max_chars', 12000)
        if max_chars == 0:
            max_chars = None
        try:
            context = url_to_context(
                args.url,
                config['printer']['width'],
                max_chars,
                link_qr=True,
                link_qr_size=int(config.get('printer', {}).get('link_qr_size', 5)),
            )
        except Exception as exc:
            print(f'Error fetching URL: {exc}', file=sys.stderr)
            return
        template_name = getattr(args, 'template', None) or context.get('template', 'note')
        if context.get('truncated'):
            print('[printime] Article truncated — use --max-chars 0 for full text', file=sys.stderr)
        _print_template(
            printer, config, template_name, context,
            preview=args.preview, yes=getattr(args, 'yes', False),
            no_cut=getattr(args, 'no_cut', False), label='URL',
        )
        if not args.preview:
            print(f"URL printed: {args.url}")
        return

    if args.md:
        from printime.services.transform import markdown_to_context
        with open(args.md, 'r') as f:
            content = f.read()
        context = markdown_to_context(
            content,
            args.md,
            config['printer']['width'],
            link_qr=getattr(args, 'link_qr', False),
            link_qr_size=int(config.get('printer', {}).get('link_qr_size', 5)),
        )
        template_name = getattr(args, 'template', None) or context.get('template', 'note')

        png_path = _resolve_context_image(context, config)
        if png_path and not _uses_segment_print(context, template_name):
            context['image_path'] = png_path

        try:
            _print_template(
                printer, config, template_name, context,
                preview=args.preview, yes=getattr(args, 'yes', False),
                no_cut=getattr(args, 'no_cut', False),
                png_path=png_path if not _uses_segment_print(context, template_name) else None,
                label='Markdown',
            )
            if not args.preview:
                print('Markdown printed')
        except PermissionError:
            print('ERROR: Permission denied. Run \'newgrp lp\' first or check /dev/usb/lp5 permissions')
        except Exception as e:
            print(f'ERROR: Print failed - {e}')
        return

    if args.template:
        context = {}
        if args.file:
            context = load_context_file(args.file)
        else:
            if getattr(args, 'title', None):
                context['title'] = args.title
            if getattr(args, 'content', None):
                context['content'] = args.content
            elif args.text:
                context['content'] = args.text
            if getattr(args, 'priority', None):
                context['priority'] = args.priority
            if getattr(args, 'tags', None):
                context['tags'] = [t.strip() for t in args.tags.split(',')]

        from printime.services.enrich import enrich_context_fields
        context = enrich_context_fields(
            context,
            config['printer']['width'],
            markdown=True,
            link_qr=getattr(args, 'link_qr', False),
            link_qr_size=int(config.get('printer', {}).get('link_qr_size', 5)),
        )
        if context.get('segments') and not args.template:
            args.template = context.get('template', 'document')

        _print_template(
            printer, config, args.template, context,
            preview=args.preview, yes=getattr(args, 'yes', False),
            no_cut=getattr(args, 'no_cut', False), label='Template',
        )
        return

    if getattr(args, 'ascii', None):
        from printime.services.ascii_art import render_ascii_art

        width = config['printer']['width']
        align = 'center' if args.center else 'left'
        rendered = render_ascii_art(
            args.ascii,
            font=getattr(args, 'ascii_font', 'slant'),
            width=width,
            align=align,
            api_fallback=bool(getattr(args, 'ascii_api_fallback', False)),
            strict=bool(getattr(args, 'ascii_strict', False)),
        )
        context = {
            'title': getattr(args, 'title', '') or '',
            'segments': [{
                'type': 'ascii_art',
                'text': rendered.plain_text,
                'font': rendered.font,
                'align': align,
                'lines': rendered.lines,
                'chunks': rendered.chunks,
                'warnings': rendered.warnings,
            }],
        }
        from printime.preview import _render_segments_preview
        if args.preview:
            print(_render_segments_preview(context, width=width))
            if not getattr(args, 'yes', False):
                print('Preview only. Add --yes to print.')
                return
        print_segments(printer, config, 'document', context, cut=not args.no_cut)
        print('Text printed')
        return

    if args.text:
        from printime.preview import render_styled_text_preview, render_text_preview
        from printime.services.enrich import looks_like_markdown
        from printime.styled import markdown_to_print_lines

        width = config['printer']['width']
        use_markdown = getattr(args, 'markdown', False) or looks_like_markdown(args.text)
        link_qr = getattr(args, 'link_qr', False)

        if use_markdown:
            from printime.services.markdown_blocks import build_print_segments, should_use_segment_print
            context = {
                'title': getattr(args, 'title', '') or '',
                'segments': build_print_segments(
                    args.text,
                    width,
                    link_qr=link_qr,
                    link_qr_size=int(config.get('printer', {}).get('link_qr_size', 5)),
                ),
            }
            if should_use_segment_print(context['segments'], 'document'):
                from printime.preview import _render_segments_preview
                if args.preview:
                    print(_render_segments_preview(context, width=width))
                    if not getattr(args, 'yes', False):
                        print('Preview only. Add --yes to print.')
                        return
                print_segments(printer, config, 'document', context, cut=not args.no_cut)
                print('Text printed')
                return
            lines = markdown_to_print_lines(args.text, width)
            if args.preview:
                print(render_styled_text_preview(lines, width=width))
                if not getattr(args, 'yes', False):
                    print('Preview only. Add --yes to print.')
                    return
            print_styled_lines(printer, lines, width=width)
            if not args.no_cut:
                printer.cut()
            print('Text printed')
            return

        align = 'center' if args.center else 'left'
        if args.preview:
            print(render_text_preview(
                args.text, width=width, bold=args.bold, align=align,
            ))
            if not getattr(args, 'yes', False):
                print('Preview only. Add --yes to print.')
                return
        printer.text(args.text, bold=args.bold, align=align)
        if not args.no_cut:
            printer.cut()
        print('Text printed')
        return

    print(
        'Nothing to print. Use --text, --ascii, --template, --qr, --url, or a file.',
        file=sys.stderr,
    )


def _get_template_dir() -> str:
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return template_dir


def _load_template_catalog() -> dict[str, dict]:
    import yaml

    catalog: dict[str, dict] = {}
    template_dir = _get_template_dir()
    if not os.path.exists(template_dir):
        return catalog
    for f in os.listdir(template_dir):
        if not f.endswith('.yaml'):
            continue
        name = f[:-5]
        with open(os.path.join(template_dir, f), 'r') as yf:
            catalog[name] = yaml.safe_load(yf) or {}
    return catalog


def _format_template_field(field) -> str:
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        parts = []
        for key, value in field.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                subkeys = ', '.join(value[0].keys())
                parts.append(f'{key}: [{{{subkeys}}}]')
            elif value is None:
                parts.append(f'{key}')
            else:
                parts.append(f'{key}: {value}')
        return ', '.join(parts)
    return str(field)


def _print_template_entry(name: str, data: dict, *, verbose: bool = False) -> None:
    desc = data.get('description', 'No description')
    if not verbose:
        print(f'  {name:<15} - {desc}')
        return

    print(f'{name}')
    print(f'  {desc}')
    fields = data.get('fields', [])
    if fields:
        print('  Fields:')
        for field in fields:
            print(f'    - {_format_template_field(field)}')
    if name == 'agenda':
        print('  Command:')
        print('    printime agenda --preview')
    elif name == 'checklist':
        print('  Example:')
        print('    printime print examples/checklist.md --preview')
    else:
        print('  Example:')
        print(f'    printime print --template {name} --title "..." --content "..." --preview')


def cmd_list(args) -> int:
    catalog = _load_template_catalog()
    if not catalog:
        print('No templates found.', file=sys.stderr)
        return 1

    template_name = getattr(args, 'template', None)
    if template_name:
        if template_name not in catalog:
            print(f'Unknown template: {template_name}', file=sys.stderr)
            print(f'Available: {", ".join(sorted(catalog))}', file=sys.stderr)
            return 1
        _print_template_entry(template_name, catalog[template_name], verbose=True)
        return 0

    verbose = getattr(args, 'verbose', False)
    if verbose:
        print('Templates (use: printime list <name> for one, printime <cmd> --help for flags)\n')
    for name in sorted(catalog):
        _print_template_entry(name, catalog[name], verbose=verbose)
        if verbose:
            print()
    return 0


def cmd_ascii_fonts() -> int:
    """List limited ASCII-art fonts supported for thermal printing."""
    from printime.services.ascii_art import supported_fonts_help

    print(supported_fonts_help())
    return 0


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
    from printime.cli_epilog import MAIN_EPILOG, PRINT_EPILOG, TEMPLATE_CHOICES_HELP
    from printime.cli_help import HelpfulArgumentParser, PARSER_REGISTRY
    from printime.services.ascii_art import supported_font_names

    parser = HelpfulArgumentParser(
        description='Printime - Thermal Printer CLI',
        prog='printime',
        epilog=MAIN_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    PARSER_REGISTRY[''] = parser
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 0.1.0')
    subparsers = parser.add_subparsers(dest='command', help='Commands', parser_class=HelpfulArgumentParser)

    print_parser = subparsers.add_parser(
        'print',
        help='Print text, QR, templates, markdown, URLs, tickets',
        epilog=PRINT_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    PARSER_REGISTRY['print'] = print_parser
    print_parser.add_argument('input', nargs='?', help='Input file (.md, .pdf, .json, .yaml)')
    print_parser.add_argument('--file', '-f', help='Context file (.md, .json, or .yaml)')
    print_parser.add_argument('--md', help='Print markdown file (.md)')
    print_parser.add_argument('--text', '-t', help='Text to print')
    print_parser.add_argument('--markdown', '-m', action='store_true',
                              help='Parse --text / --content as markdown (# headings, **bold**, lists)')
    print_parser.add_argument(
        '--template',
        help=f'Template name ({TEMPLATE_CHOICES_HELP}; printime list <name> for fields)',
    )
    print_parser.add_argument('--title', help='Title for template')
    print_parser.add_argument('--content', help='Content for template')
    print_parser.add_argument('--priority', help='Priority (HIGH, MEDIUM, LOW)')
    print_parser.add_argument('--tags', help='Tags (comma-separated)')
    print_parser.add_argument('--url', help='Fetch and print a web article (blog post, Substack, etc.)')
    print_parser.add_argument('--max-chars', type=int, default=12000,
                              help='Max article characters for --url (0 = no limit, default: 12000)')
    print_parser.add_argument('--ticket', help='Print ticket PDF (extract QR/barcodes in order)')
    print_parser.add_argument('--image', help='Print a PNG/JPG image file')
    print_parser.add_argument('--mermaid', help='Render a .mmd file (mermaid-cli) and print')
    print_parser.add_argument('--qr', help='Print QR code with data')
    print_parser.add_argument('--qr-size', type=int, default=8,
                              help='QR module size 4-12, default 8 (larger = bigger code)')
    print_parser.add_argument('--show-link', action='store_true',
                              help='Print the URL text below the QR code')
    print_parser.add_argument('--link-qr', action='store_true',
                              help='Add mini QR codes for URLs in markdown or --url articles')
    print_parser.add_argument('--bold', action='store_true', help='Bold text')
    print_parser.add_argument('--center', action='store_true', help='Center align')
    print_parser.add_argument('--double-height', action='store_true', help='Double height text')
    print_parser.add_argument('--ascii', help='Render text as receipt-safe ASCII art')
    print_parser.add_argument(
        '--ascii-font',
        choices=supported_font_names(),
        default='slant',
        help='ASCII art font for --ascii (limited thermal-safe choices)',
    )
    print_parser.add_argument('--ascii-api-fallback', action='store_true',
                              help='Use asciified API if local pyfiglet rendering fails')
    print_parser.add_argument('--ascii-strict', action='store_true',
                              help='Fail if the requested ASCII font cannot fit')
    print_parser.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')
    print_parser.add_argument('--yes', '-y', action='store_true', help='Print immediately, or print after preview')
    print_parser.add_argument('--no-cut', action='store_true', help='Do not cut paper')
    print_parser.add_argument('--test', choices=['qr', 'text', 'all'], help='Run test print')

    serve_parser = subparsers.add_parser('serve', help='Start HTTP server')
    serve_parser.add_argument('--port', '-p', type=int, default=8080, help='Port (default: 8080)')

    list_parser = subparsers.add_parser(
        'list',
        help='List templates and their fields',
        description='List built-in templates. Pass a template name for field details, '
                    'or use --verbose for all. Command flags: printime <command> --help',
    )
    list_parser.add_argument('template', nargs='?', help='Show fields for one template (e.g. note)')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Show fields for every template')

    subparsers.add_parser(
        'ascii-fonts',
        help='List supported ASCII art fonts',
        description='List the limited thermal-safe ASCII art fonts supported by printime.',
    )

    doctor_parser = subparsers.add_parser('doctor', help='Diagnose printer setup')
    doctor_parser.add_argument('--test-print', action='store_true', help='Send a test page')

    preview_parser = subparsers.add_parser('preview', help='Preview what will be printed')
    preview_parser.add_argument('--text', '-t', help='Text to preview')
    preview_parser.add_argument('--template', help='Template to preview')
    preview_parser.add_argument('--title', help='Title for template preview')
    preview_parser.add_argument('--content', help='Content for template preview')
    preview_parser.add_argument('--file', '-f', help='Context file (.md, .json, or .yaml)')
    preview_parser.add_argument('--no-cut', action='store_true', help='Do not cut paper after printing')
    preview_parser.add_argument('--yes', '-y', action='store_true', help='Print after preview')

    transform_parser = subparsers.add_parser('transform', help='Transform file to print format')
    transform_parser.add_argument('input', nargs='?', help='Input file path (.md, .tex, .txt)')
    transform_parser.add_argument('--type', '-t', choices=['context', 'text', 'image'],
                                   help='Output type (auto-detected from extension)')
    transform_parser.add_argument('--template', help='Template to wrap result in')
    transform_parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    transform_parser.add_argument('--url', help='Fetch a web article instead of a local file')
    transform_parser.add_argument('--max-chars', type=int, default=12000,
                                  help='Max article characters for --url (0 = no limit)')
    transform_parser.add_argument('--yes', '-y', action='store_true', help='Print after preview')
    transform_parser.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')

    anytype_parser = subparsers.add_parser('anytype', help='Anytype integration')
    PARSER_REGISTRY['anytype'] = anytype_parser
    anytype_sub = anytype_parser.add_subparsers(dest='anytype_cmd', parser_class=HelpfulArgumentParser)
    anytype_list = anytype_sub.add_parser('list', help='List Anytype spaces')
    anytype_join = anytype_sub.add_parser('join', help='Join a space via invite link')
    anytype_join.add_argument('invite_link', nargs='?', help='Invite link from Anytype Desktop')
    anytype_join.add_argument('--file', '-f', help='File with one invite link per line')
    anytype_fetch = anytype_sub.add_parser('fetch', help='Fetch a page')
    anytype_fetch.add_argument('page_id', help='Page ID to fetch')
    anytype_fetch.add_argument('--space', '-s', help='Space ID (optional; searches all joined spaces by default)')
    anytype_fetch.add_argument('--template', '-t', help='Template to use')
    anytype_fetch.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')
    anytype_search = anytype_sub.add_parser('search', help='Search pages across all spaces')
    anytype_search.add_argument('query', help='Search text')
    anytype_print = anytype_sub.add_parser('print', help='Search by title and print')
    PARSER_REGISTRY['anytype.print'] = anytype_print
    anytype_print.add_argument('query', help='Page title or search text')
    anytype_print.add_argument('--template', '-t', help='Template to use')
    anytype_print.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')
    anytype_print.add_argument('--yes', '-y', action='store_true', help='Print after preview')

    keep_parser = subparsers.add_parser('keep', help='Google Keep integration')
    PARSER_REGISTRY['keep'] = keep_parser
    keep_sub = keep_parser.add_subparsers(dest='keep_cmd', parser_class=HelpfulArgumentParser)
    keep_list = keep_sub.add_parser('list', help='List recent Keep notes')
    keep_search = keep_sub.add_parser('search', help='Search Keep notes by title/text')
    keep_search.add_argument('query', help='Search text')
    keep_print = keep_sub.add_parser('print', help='Print a note by URL or ID')
    PARSER_REGISTRY['keep.print'] = keep_print
    keep_print.add_argument('target', help='Keep URL (#NOTE/...) or note ID')
    keep_print.add_argument('--template', '-t', help='Template to use')
    keep_print.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')
    keep_print.add_argument('--yes', '-y', action='store_true', help='Print after preview')

    agenda_parser = subparsers.add_parser('agenda', help="Print Google Calendar agenda")
    agenda_parser.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')
    agenda_parser.add_argument('--yes', '-y', action='store_true', help='Print after preview')
    agenda_parser.add_argument('--days', type=int, default=1, help='Number of days to include (default: 1)')
    agenda_range = agenda_parser.add_mutually_exclusive_group()
    agenda_range.add_argument(
        '--today',
        action='store_true',
        help="Print today's agenda (explicit default)",
    )
    agenda_range.add_argument(
        '--next-week',
        action='store_true',
        help='Print Mon–Sun of the upcoming week',
    )
    agenda_parser.add_argument('--ics-url', help='Override GOOGLE_CALENDAR_ICS_URL from .env')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    config = load_config()

    if args.command == 'print':
        resolve_print_input(args)
        _resolve_print_file_args(args)
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
        return cmd_list(args)
    elif args.command == 'ascii-fonts':
        return cmd_ascii_fonts()

    elif args.command == 'preview':
        from printime.preview import render_template_preview
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
            from printime.preview import render_text_preview

            width = config['printer']['width']
            align = 'center' if getattr(args, 'center', False) else 'left'
            print(render_text_preview(
                args.text,
                width=width,
                bold=getattr(args, 'bold', False),
                align=align,
            ))
            if auto_yes:
                printer = create_printer(config)
                try:
                    printer.text(args.text, bold=getattr(args, 'bold', False), align='center' if getattr(args, 'center', False) else 'left')
                    if not no_cut:
                        printer.cut()
                finally:
                    finish_job(printer)
                print("Printed successfully")
            else:
                print("Preview only. Add --yes to print.")
        elif args.file or context or getattr(args, 'title', None) or getattr(args, 'content', None):
            rendered = render_template_preview(template_name, context)
            print(rendered)
            if auto_yes:
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
                print("Preview only. Add --yes to print.")
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
            from printime.preview import render_template_preview
            template_name = args.template or result['content'].get('template', 'note')
            rendered = render_template_preview(template_name, result['content'])
            print(rendered)
            auto_yes = getattr(args, 'yes', False)
            if auto_yes:
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
                print("Preview only. Add --yes to print.")

    elif args.command == 'anytype':
        if args.anytype_cmd is None:
            anytype_parser.print_help()
            print(
                '\nExamples:\n'
                '  printime anytype print "Page title" --preview\n'
                '  printime anytype search "query"\n'
                '  printime anytype list',
                file=sys.stderr,
            )
            return 2
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
                yes=getattr(args, 'yes', False),
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

    elif args.command == 'keep':
        if args.keep_cmd is None:
            keep_parser.print_help()
            print(
                '\nExamples:\n'
                '  printime keep print "https://keep.google.com/#NOTE/abc..." --preview\n'
                '  printime keep search "shopping"\n'
                '  printime keep list',
                file=sys.stderr,
            )
            return 2
        from printime.services.keep import list_notes, print_keep_note, search_notes

        if args.keep_cmd == 'print':
            try:
                print_keep_note(
                    args.target,
                    preview=getattr(args, 'preview', False),
                    yes=getattr(args, 'yes', False),
                    template=getattr(args, 'template', None),
                    config=config,
                )
            except ImportError as exc:
                print(f'Error: {exc}', file=sys.stderr)
                return 1
            except ValueError as exc:
                print(f'Error: {exc}', file=sys.stderr)
                return 1
        elif args.keep_cmd == 'search':
            try:
                hits = search_notes(args.query)
            except (ImportError, ValueError) as exc:
                print(f'Error: {exc}', file=sys.stderr)
                return 1
            if not hits:
                print(f'No Keep notes for: {args.query!r}')
                return 1
            for row in hits:
                print(f"  {row['title']:<40} {row['id']}")
        elif args.keep_cmd == 'list':
            try:
                rows = list_notes()
            except (ImportError, ValueError) as exc:
                print(f'Error: {exc}', file=sys.stderr)
                return 1
            for row in rows:
                pin = '*' if row['pinned'] else ' '
                print(f" {pin} {row['title']:<38} {row['id']}")

    elif args.command == 'agenda':
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
    raise SystemExit(main() or 0)