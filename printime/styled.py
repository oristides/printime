#!/usr/bin/env python3
"""Styled line model for ESC/POS thermal printing."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from typing import List, Tuple

STYLED_CONTENT_MARKER = '\n\x1eSTYLED_CONTENT\x1e\n'


@dataclass
class PrintLine:
    text: str
    align: str = 'left'
    bold: bool = False
    double_height: bool = False
    double_width: bool = False


def effective_columns(width: int, line: PrintLine) -> int:
    cols = width
    if line.double_width:
        cols = max(1, cols // 2)
    return cols


def normalize_markdown_text(text: str) -> str:
    """Normalize line endings and split jammed block markers onto their own lines."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split headings that were jammed onto one line after whitespace.
    text = re.sub(r' +(?=#{1,6}\s+)', '\n', text)
    return text


def split_physical_line(line: str) -> List[str]:
    """Split one source line that contains multiple markdown headings."""
    stripped = line.strip()
    if not stripped:
        return ['']
    if not re.search(r'#{1,6}\s+', stripped):
        return [stripped]
    parts = re.split(r'\s+(?=(?:#{1,6})\s+)', stripped)
    return [part.strip() for part in parts if part.strip()]


def _clean_inline_markdown(text: str) -> Tuple[str, bool]:
    """Strip inline markdown; bold only when ** is used."""
    bold = '**' in text
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', clean)
    clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
    clean = re.sub(r'`(.+?)`', r'\1', clean)
    return clean.strip(), bold


def _heading_line(level: int, text: str) -> PrintLine:
    clean, bold = _clean_inline_markdown(text)
    centered = False
    center_match = re.match(r'^<center>(.*)</center>$', clean, re.IGNORECASE)
    if center_match:
        clean = center_match.group(1).strip()
        centered = True
    align = 'center' if centered else 'left'
    if level == 1:
        return PrintLine(clean, align=align, bold=bold, double_height=True, double_width=True)
    if level == 2:
        return PrintLine(clean, align=align, bold=bold, double_height=True)
    if level == 3:
        return PrintLine(clean, align=align, bold=bold, double_width=True)
    return PrintLine(clean, align=align, bold=bold or level >= 4)


def markdown_to_print_lines(body: str, width: int = 48) -> List[PrintLine]:
    """Parse markdown body into ESC/POS styled lines."""
    content = normalize_markdown_text(body.strip())
    content = re.sub(r'```[\s\S]*?```', '', content)

    lines: List[PrintLine] = []
    for line in content.split('\n'):
        if not line.strip():
            lines.append(PrintLine(''))
            continue

        for stripped in split_physical_line(line):
            heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
            if heading:
                level = len(heading.group(1))
                lines.append(_heading_line(level, heading.group(2)))
                continue

            if re.match(r'^\s*[-*+]\s+', stripped) or re.match(r'^\s*\d+\.\s+', stripped):
                bullet = re.sub(r'^\s*[-*+]\s+', '* ', stripped)
                bullet = re.sub(r'^\s*\d+\.\s+', '* ', bullet)
                clean, bold = _clean_inline_markdown(bullet)
                wrapped = textwrap.fill(clean, width=width, subsequent_indent='  ')
                for part in wrapped.split('\n'):
                    lines.append(PrintLine(part, bold=bold))
                continue

            clean, bold = _clean_inline_markdown(stripped)
            centered = False
            center_match = re.match(r'^<center>(.*)</center>$', clean, re.IGNORECASE)
            if center_match:
                clean = center_match.group(1).strip()
                centered = True
            wrapped = textwrap.fill(clean, width=width)
            for part in wrapped.split('\n'):
                lines.append(PrintLine(part, bold=bold, align='center' if centered else 'left'))

    return lines


def format_print_line(line: PrintLine, width: int = 48) -> str:
    """Layout one styled line for preview (simulates ESC/POS alignment and width)."""
    if not line.text:
        return ''
    cols = effective_columns(width, line)
    text = line.text[:cols]
    if line.align == 'center':
        chunk = text.center(cols)
        pad = max(0, (width - len(chunk)) // 2)
        return ((' ' * pad) + chunk)[:width].ljust(width)
    if line.align == 'right':
        chunk = text.rjust(cols)
        pad = max(0, width - len(chunk))
        return (' ' * pad + chunk)[:width].ljust(width)
    return text.ljust(width)[:width]


def lines_to_plain_preview(lines: List[PrintLine], width: int = 48) -> str:
    """Plain text for terminal preview (paper uses ESC/POS sizes, not bars)."""
    parts: List[str] = []
    for line in lines:
        if not line.text:
            parts.append('')
            continue
        parts.append(format_print_line(line, width))
    return '\n'.join(parts).strip()


def format_markdown_for_print(body: str, width: int = 48) -> str:
    """Plain-text layout (same as preview helper)."""
    if not body.strip():
        return ''
    return lines_to_plain_preview(markdown_to_print_lines(body, width), width)
