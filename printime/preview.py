#!/usr/bin/env python3
"""
Printime - Terminal Preview Module

Renders print output as it will appear on 80mm thermal paper.
Preview includes terminal borders and a [CUT] guide (not printed on paper).
"""

import os
import re
import sys
from typing import List

BOLD = '\033[1m'
BOLD_OFF = '\033[0m'
WIDTH = 48
BORDER_LEFT = '|'
BORDER_RIGHT = '|'
INNER_WIDTH = WIDTH


def center_text(text: str, width: int = INNER_WIDTH) -> str:
    return text.center(width)


def ljust_text(text: str, width: int = INNER_WIDTH) -> str:
    return text.ljust(width)


def rjust_text(text: str, width: int = INNER_WIDTH) -> str:
    return text.rjust(width)


def truncate_text(text: str, width: int = INNER_WIDTH) -> str:
    if len(text) <= width:
        return text
    return text[:width - 3] + '...'


def sanitize_printer_text(text: str) -> str:
    """Convert text to ASCII-safe content for thermal printers."""
    replacements = {
        '•': '*',
        '–': '-',
        '—': '-',
        '‘': "'",
        '’': "'",
        '“': '"',
        '”': '"',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode('ascii', errors='replace').decode('ascii')


class PaperPreview:
    """Renders content as it would appear on thermal paper (terminal only)."""

    def __init__(self, width: int = INNER_WIDTH, *, framed: bool = True):
        self.width = width
        self.lines: List[str] = []
        if framed:
            self._add_border_top()

    def add_title_header(self, title: str, caption: str | None = None) -> None:
        """Title block: === lines with title and optional caption from frontmatter."""
        self._add_separator('=')
        self._add_line(title.upper().ljust(self.width))
        if caption:
            self._add_line(caption.ljust(self.width))
        self._add_separator('=')
        self._add_blank()

    def _add_border_top(self):
        self.lines.append(BORDER_LEFT + '=' * self.width + BORDER_RIGHT)

    def _add_border_bottom(self):
        self.lines.append(BORDER_LEFT + '=' * self.width + BORDER_RIGHT)

    def _add_line(self, content: str, bold: bool = False):
        if bold:
            content = f"{BOLD}{content}{BOLD_OFF}"
        self.lines.append(BORDER_LEFT + content.ljust(self.width) + BORDER_RIGHT)

    def _add_blank(self):
        self.lines.append(BORDER_LEFT + ' ' * self.width + BORDER_RIGHT)

    def _add_separator(self, char: str = '-'):
        self.lines.append(BORDER_LEFT + char * self.width + BORDER_RIGHT)

    def _add_cut_guide(self):
        """Preview-only cut indicator — never sent to the printer."""
        self._add_blank()
        self._add_separator('-')
        dotted = ' ' + '- ' * (self.width // 2)
        self.lines.append(BORDER_LEFT + dotted[:self.width + 1] + BORDER_RIGHT)
        self._add_blank()
        self.lines.append(BORDER_LEFT + ' ' + '[CUT]'.center(self.width) + ' ' + BORDER_RIGHT)
        self._add_blank()

    def footer(self):
        self._add_cut_guide()
        self._add_border_bottom()

    def render(self) -> str:
        return '\n'.join(self.lines)


def confirm(prompt: str = "Print this?") -> bool:
    if not sys.stdin.isatty():
        return True
    response = input(f"\n{BOLD}{prompt} [Y/n]: {BOLD_OFF}").strip().lower()
    return response in ('', 'y', 'yes')


def _get_template_dir() -> str:
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    if not os.path.exists(template_dir):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return template_dir


def _get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def _render_jinja_template(template_name: str, context: dict, width: int = INNER_WIDTH) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(_get_template_dir()),
        autoescape=select_autoescape(),
    )
    env.filters['center'] = lambda s, w=width: center_text(str(s), w)
    env.filters['ljust'] = lambda s, w=width: ljust_text(str(s), w)
    env.filters['rjust'] = lambda s, w=width: rjust_text(str(s), w)
    env.filters['truncate'] = lambda s, w=width: truncate_text(str(s), w)

    template = env.get_template(f'{template_name}.j2')
    ctx = {'width': width, 'now': _get_timestamp()}
    ctx.update(context)
    return template.render(**ctx)


def render_text_preview(
    text: str,
    *,
    width: int = INNER_WIDTH,
    bold: bool = False,
    align: str = 'left',
) -> str:
    """Terminal preview for plain text with borders and [CUT] guide."""
    preview = PaperPreview(width=width)
    line = sanitize_printer_text(text)
    if align == 'center':
        line = center_text(line, width)
    elif align == 'right':
        line = rjust_text(line, width)
    else:
        line = ljust_text(line, width)
    preview._add_line(line, bold=bold)
    preview.footer()
    return preview.render()


def render_image_preview(
    image_path: str,
    *,
    title: str | None = None,
    caption: str | None = None,
    width: int = INNER_WIDTH,
) -> str:
    """Terminal preview for image print jobs."""
    preview = PaperPreview(width=width)
    if title:
        preview._add_line(title, bold=True)
        preview._add_separator('=')
    preview._add_line(f'[image: {os.path.basename(image_path)}]')
    if caption:
        preview._add_line(caption)
    preview.footer()
    return preview.render()


def _append_rendered_lines(preview: PaperPreview, rendered: str) -> None:
    for line in rendered.split('\n'):
        if not line.strip():
            preview._add_blank()
        else:
            preview._add_line(line)


def _append_styled_lines(preview: PaperPreview, lines, width: int = INNER_WIDTH) -> None:
    from printime.styled import PrintLine, format_print_line

    for line in lines:
        if not isinstance(line, PrintLine):
            continue
        if not line.text:
            preview._add_blank()
            continue
        formatted = format_print_line(line, width)
        preview._add_line(formatted, bold=line.bold or line.double_height)


def _render_segments_preview(context: dict, width: int = INNER_WIDTH) -> str:
    preview = PaperPreview(width=width, framed=False)
    title = context.get('title', '')
    caption = context.get('caption')
    if title:
        preview.add_title_header(title, caption=caption)

    for seg in context.get('segments', []):
        seg_type = seg.get('type')
        if seg_type == 'styled':
            _append_styled_lines(preview, seg.get('lines') or [], width=width)
        elif seg_type == 'items':
            preview._add_blank()
            for item in seg.get('items') or []:
                mark = 'X' if item.get('checked') else ' '
                preview._add_line(f"[{mark}] {item.get('text', '')}")
            preview._add_blank()
        elif seg_type == 'mermaid':
            preview._add_line('[diagram]')
            preview._add_blank()
        elif seg_type == 'qr':
            from printime.services.markdown_blocks import QR_SIZE_DEFAULT

            data = seg.get('data', '')
            size = seg.get('qr_size', QR_SIZE_DEFAULT)
            extra = []
            if size != QR_SIZE_DEFAULT:
                extra.append(f"size={size}")
            if seg.get('show_link'):
                extra.append('show-link')
            if seg.get('center'):
                extra.append('center')
            opts = f" ({', '.join(extra)})" if extra else ''
            label = f"[QR]{opts} {data}"
            preview._add_line(truncate_text(label, width))
            preview._add_blank()

    preview.footer()
    return preview.render()


def render_template_preview(
    template_name: str,
    context: dict,
    width: int = INNER_WIDTH,
    *,
    styled_lines=None,
    styled_field: str | None = None,
) -> str:
    """Terminal preview with borders and [CUT] guide."""
    from printime.services.markdown_blocks import should_use_segment_print

    if should_use_segment_print(context.get('segments') or [], template_name):
        return _render_segments_preview(context, width)

    from printime.styled import STYLED_CONTENT_MARKER

    render_ctx = dict(context)
    marker = STYLED_CONTENT_MARKER.strip()
    if styled_lines and styled_field:
        render_ctx[styled_field] = marker

    try:
        rendered = _render_jinja_template(template_name, render_ctx, width)
    except Exception:
        return f"Template '{template_name}' not found"

    preview = PaperPreview(width=width)
    if styled_lines and marker in rendered:
        before, _, after = rendered.partition(marker)
        if before:
            _append_rendered_lines(preview, before.rstrip('\n'))
        _append_styled_lines(preview, styled_lines, width=width)
        if after:
            _append_rendered_lines(preview, after.lstrip('\n'))
    else:
        _append_rendered_lines(preview, rendered)
    preview.footer()
    return preview.render()


def render_template_for_print(template_name: str, context: dict, config: dict) -> str:
    """Paper output — same template layout, no borders or [CUT] guide."""
    width = config['printer']['width']
    try:
        rendered = _render_jinja_template(template_name, context, width)
    except Exception:
        return ''
    return sanitize_printer_text(rendered)
