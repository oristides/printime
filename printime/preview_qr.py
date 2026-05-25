#!/usr/bin/env python3
"""Proportional ASCII QR preview matching thermal print size."""

from __future__ import annotations

import math
from typing import List, Tuple

import qrcode

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

QR_BORDER_MODULES = 2
QR_EC = qrcode.constants.ERROR_CORRECT_M


def qr_print_pixel_width(data: str, qr_size: int = 8, border: int = QR_BORDER_MODULES) -> Tuple[int, int]:
    """Return (pixel_width_on_paper, module_count) using same params as print path."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=QR_EC,
        box_size=1,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    modules = len(qr.get_matrix()[0])
    pixels = modules * qr_size
    return pixels, modules


def render_qr_ascii(
    data: str,
    *,
    qr_size: int = 8,
    paper_width_pixels: int = 576,
    paper_cols: int = 48,
    center: bool = True,
    align: str | None = None,
) -> List[str]:
    """Return QR lines sized to match printed proportion on paper_cols."""
    if align is None:
        align = 'center' if center else 'left'
    if not data:
        return []

    qr = qrcode.QRCode(
        version=None,
        error_correction=QR_EC,
        box_size=1,
        border=QR_BORDER_MODULES,
    )
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    if cols == 0:
        return []

    print_px, _ = qr_print_pixel_width(data, qr_size=qr_size)
    on_paper_px = min(print_px, paper_width_pixels)
    fraction = on_paper_px / max(paper_width_pixels, 1)
    target_cols = max(8, int(paper_cols * fraction))

    # Two terminal columns per module (██).
    raw_width = cols * 2
    step = 1
    if raw_width > target_cols:
        step = max(1, math.ceil(cols / (target_cols / 2)))

    lines: List[str] = []
    for r in range(0, rows, step):
        chars = []
        for c in range(0, cols, step):
            chars.append('██' if matrix[r][c] else '  ')
        line = ''.join(chars)
        if len(line) > paper_cols:
            line = line[:paper_cols]
        lines.append(line)

    if align == 'center' and lines:
        max_len = max(len(line) for line in lines)
        pad = max(0, (paper_cols - max_len) // 2)
        if pad:
            lines = [' ' * pad + line for line in lines]
    elif align == 'right' and lines:
        max_len = max(len(line) for line in lines)
        pad = max(0, paper_cols - max_len)
        if pad:
            lines = [' ' * pad + line for line in lines]

    return lines


def make_aligned_qr_image(
    data: str,
    *,
    qr_size: int = 8,
    paper_width_pixels: int = 576,
    align: str = 'center',
    border: int = QR_BORDER_MODULES,
):
    """Render QR bitmap aligned on paper (used by USB/raw print backends)."""
    if Image is None or not data:
        return None
    qr = qrcode.QRCode(
        version=None,
        error_correction=QR_EC,
        box_size=qr_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('1')
    w, h = img.size
    if w >= paper_width_pixels or align == 'left':
        return img
    padded = Image.new('1', (paper_width_pixels, h), 1)
    if align == 'center':
        x = (paper_width_pixels - w) // 2
    elif align == 'right':
        x = paper_width_pixels - w
    else:
        x = 0
    padded.paste(img, (x, 0))
    return padded


def render_qr_ascii_block(
    data: str,
    *,
    qr_size: int = 8,
    paper_width_pixels: int = 576,
    paper_cols: int = 48,
    center: bool = True,
    align: str | None = None,
) -> str:
    return '\n'.join(
        render_qr_ascii(
            data,
            qr_size=qr_size,
            paper_width_pixels=paper_width_pixels,
            paper_cols=paper_cols,
            center=center,
            align=align,
        )
    )
