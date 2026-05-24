#!/usr/bin/env python3
"""Text normalization for preview vs printer encoding."""

from __future__ import annotations

import unicodedata
from typing import Literal

PrinterEncoding = Literal['cp850', 'latin-1', 'ascii', 'utf-8']

# Common punctuation → ASCII-safe substitutes (preview + print).
_CHAR_MAP = {
    '•': '*',
    '–': '-',
    '—': '-',
    '‘': "'",
    '’': "'",
    '“': '"',
    '”': '"',
    '…': '...',
}


def normalize_unicode_text(text: str) -> str:
    """Normalize punctuation; keep accented letters for preview and cp850 print."""
    for src, dst in _CHAR_MAP.items():
        text = text.replace(src, dst)
    return text


def normalize_for_preview(text: str) -> str:
    """Preview text — preserve Portuguese/European characters (ã, ç, é)."""
    return normalize_unicode_text(text)


def encode_for_printer(text: str, encoding: PrinterEncoding = 'cp850') -> bytes:
    """Encode text for ESC/POS; cp850 covers Western European Latin."""
    text = normalize_unicode_text(text)
    if encoding == 'ascii':
        text = unicodedata.normalize('NFKD', text)
        return text.encode('ascii', errors='ignore')
    try:
        return text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        text = unicodedata.normalize('NFKD', text)
        return text.encode('ascii', errors='ignore')


def decode_for_display(data: bytes, encoding: PrinterEncoding = 'cp850') -> str:
    try:
        return data.decode(encoding)
    except Exception:
        return data.decode('utf-8', errors='replace')


def sanitize_printer_text(text: str, *, encoding: PrinterEncoding = 'cp850') -> str:
    """Legacy name: normalize then round-trip through printer encoding for paper output."""
    return decode_for_display(encode_for_printer(text, encoding), encoding)
