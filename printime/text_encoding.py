#!/usr/bin/env python3
"""Text normalization for preview vs printer encoding."""

from __future__ import annotations

import unicodedata
from typing import Literal

PrinterEncoding = Literal['cp850', 'cp860', 'latin-1', 'ascii', 'utf-8']

VALID_PRINTER_ENCODINGS = frozenset({'cp850', 'cp860', 'latin-1', 'ascii', 'utf-8'})

# ESC/POS ESC t n — character code table (Epson / most 80mm clones)
ESC_POS_CODE_PAGE: dict[str, int] = {
    'cp850': 2,   # Multilingual Latin I
    'cp860': 3,   # Portuguese
    'latin-1': 16,  # WPC1252 on many Epson firmwares
}

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


def escpos_select_code_page(encoding: str | None) -> bytes | None:
    """Return ESC t n bytes to match encode_for_printer() code page."""
    enc = resolve_printer_encoding(encoding)
    page = ESC_POS_CODE_PAGE.get(enc)
    if page is None:
        return None
    return bytes([0x1B, 0x74, page])


def resolve_printer_encoding(encoding: str | None) -> PrinterEncoding:
    """Normalize encoding name from config."""
    enc = (encoding or 'cp850').lower()
    if enc in VALID_PRINTER_ENCODINGS:
        return enc  # type: ignore[return-value]
    return 'cp850'


def encode_for_printer(text: str, encoding: PrinterEncoding = 'cp850') -> bytes:
    """Encode text for ESC/POS; cp850/cp860 cover Western European Latin."""
    encoding = resolve_printer_encoding(encoding)
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


def sanitize_printer_text(text: str, *, encoding: PrinterEncoding | str = 'cp850') -> str:
    """Normalize then round-trip through printer encoding for paper output."""
    enc = resolve_printer_encoding(encoding)
    return decode_for_display(encode_for_printer(text, enc), enc)
