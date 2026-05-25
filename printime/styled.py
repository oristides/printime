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
    text = re.sub(r'(?<!\|) +(?=#{1,6}\s+)', '\n', text)
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


def _is_tableish_line(line: str) -> bool:
    stripped = line.strip()
    return '|' in stripped and not stripped.startswith('```')


def _clean_table_cell(cell: str) -> str:
    cell = re.sub(r'<br\s*/?>', ' ', cell, flags=re.IGNORECASE)
    cell = re.sub(r'^\s*#{1,6}\s+', '', cell)
    clean, _ = _clean_inline_markdown(cell)
    return re.sub(r'\s+', ' ', clean).strip()


def _parse_table_row(line: str) -> List[str]:
    line = re.sub(r'<br\s*/?>', ' ', line.strip(), flags=re.IGNORECASE)
    line = line.strip('|')
    cells = [_clean_table_cell(cell) for cell in line.split('|')]
    while cells and not cells[0]:
        cells.pop(0)
    while cells and not cells[-1]:
        cells.pop()
    return cells


def _is_table_separator(cells: List[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r':?-{3,}:?', cell.strip()) for cell in cells if cell)


def _table_column_widths(rows: List[List[str]], width: int) -> List[int]:
    columns = max(len(row) for row in rows)
    separator_width = 3 * (columns - 1)
    available = max(columns, width - separator_width)
    desired = [
        max(len(row[idx]) if idx < len(row) else 0 for row in rows)
        for idx in range(columns)
    ]
    if sum(desired) <= available:
        return [max(1, size) for size in desired]
    minimum = max(1, min(4, available // columns))
    widths = [min(size, minimum) for size in desired]
    remaining = available - sum(widths)
    while remaining > 0:
        grew = False
        by_need = sorted(
            range(columns),
            key=lambda idx: desired[idx] - widths[idx],
            reverse=True,
        )
        for idx in by_need:
            if remaining <= 0:
                break
            if widths[idx] >= desired[idx]:
                continue
            widths[idx] += 1
            remaining -= 1
            grew = True
        if not grew:
            break
    return widths


def _format_table_row(row: List[str], widths: List[int]) -> List[str]:
    wrapped = [
        textwrap.wrap(
            row[idx] if idx < len(row) else '',
            width=col_width,
            break_long_words=True,
            break_on_hyphens=False,
        ) or ['']
        for idx, col_width in enumerate(widths)
    ]
    height = max(len(parts) for parts in wrapped)
    lines = []
    for line_idx in range(height):
        cells = [
            (parts[line_idx] if line_idx < len(parts) else '').ljust(widths[idx])
            for idx, parts in enumerate(wrapped)
        ]
        lines.append(' | '.join(cells).rstrip())
    return lines


def render_markdown_table_lines(
    block: List[str],
    width: int = 48,
) -> List[PrintLine]:
    """Render a markdown/Anytype table block as thermal-friendly text rows."""
    rows: List[List[str]] = []
    saw_separator = False
    for line in block:
        cells = _parse_table_row(line)
        if not cells or not any(cells):
            continue
        if _is_table_separator(cells):
            saw_separator = True
            continue
        rows.append(cells)

    if len(rows) < 2 or max(len(row) for row in rows) < 2:
        return []

    widths = _table_column_widths(rows, width)
    rendered: List[PrintLine] = []
    for row_idx, row in enumerate(rows):
        for text in _format_table_row(row, widths):
            rendered.append(
                PrintLine(text, bold=row_idx == 0 and saw_separator)
            )
        if row_idx == 0 and saw_separator:
            rendered.append(PrintLine('-' * width))
    return rendered


def markdown_to_print_lines(body: str, width: int = 48) -> List[PrintLine]:
    """Parse markdown body into ESC/POS styled lines."""
    content = normalize_markdown_text(body.strip())
    content = re.sub(r'```[\s\S]*?```', '', content)

    lines: List[PrintLine] = []
    source_lines = content.split('\n')
    idx = 0
    while idx < len(source_lines):
        line = source_lines[idx]
        if _is_tableish_line(line):
            block = []
            while (
                idx < len(source_lines)
                and _is_tableish_line(source_lines[idx])
            ):
                block.append(source_lines[idx])
                idx += 1
            table_lines = render_markdown_table_lines(block, width)
            if table_lines:
                lines.extend(table_lines)
                continue
            for table_line in block:
                clean, bold = _clean_inline_markdown(table_line)
                lines.append(PrintLine(clean, bold=bold))
            continue

        if not line.strip():
            lines.append(PrintLine(''))
            idx += 1
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
        idx += 1

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
