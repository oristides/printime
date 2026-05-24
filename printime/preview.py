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

    def __init__(self, width: int = INNER_WIDTH):
        self.width = width
        self.lines: List[str] = []
        self._add_border_top()

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


def render_template_preview(template_name: str, context: dict, width: int = INNER_WIDTH) -> str:
    """Terminal preview with borders and [CUT] guide."""
    try:
        rendered = _render_jinja_template(template_name, context, width)
    except Exception:
        return f"Template '{template_name}' not found"

    preview = PaperPreview(width=width)
    for line in rendered.split('\n'):
        if not line.strip():
            preview._add_blank()
        else:
            preview._add_line(line)
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
