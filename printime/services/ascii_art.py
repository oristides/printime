#!/usr/bin/env python3
"""Receipt-safe ASCII art rendering."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable

ASCII_FONT_CATALOG = {
    'pagga': {
        'max_chars_hint': '~12',
        'style': 'Compact block',
        'best_for': 'short words and names',
    },
    'avatar': {
        'max_chars_hint': '~8',
        'style': 'Slim/curvy',
        'best_for': 'clean labels',
    },
    'bulbhead': {
        'max_chars_hint': '~7',
        'style': 'Curly script',
        'best_for': 'friendly headings',
    },
    'banner': {
        'max_chars_hint': '~7',
        'style': 'Hash boxes',
        'best_for': 'bold short headers',
    },
    'slant': {
        'max_chars_hint': '~8',
        'style': 'Clean diagonal',
        'best_for': 'general short text',
    },
}
SUPPORTED_FONT_NAMES = tuple(ASCII_FONT_CATALOG.keys())
SAFE_FONTS = set(SUPPORTED_FONT_NAMES)
DISCOURAGED_FONTS = {
    'the-edge',
    'the edge',
    'sub-zero',
    'banner3',
    'varsity',
    'thin',
    'shadow',
}
FONT_FALLBACKS = {
    'pagga': ('slant', 'small', 'smslant', 'mini'),
    'avatar': ('slant', 'small', 'smslant', 'mini'),
    'bulbhead': ('slant', 'small', 'smslant', 'mini'),
    'banner': ('slant', 'small', 'smslant', 'mini'),
    'slant': ('small', 'smslant', 'mini'),
}
API_FONT_NAMES = {
    'pagga': 'Pagga',
    'avatar': 'Avatar',
    'bulbhead': 'Bulbhead',
    'banner': 'Banner',
    'slant': 'Slant',
}


@dataclass(frozen=True)
class AsciiArtResult:
    plain_text: str
    font: str
    lines: list[str]
    chunks: list[str]
    warnings: list[str]


class AsciiArtError(ValueError):
    """Raised when text cannot be rendered within the receipt width."""


def supported_font_names() -> tuple[str, ...]:
    """Return public ASCII-art fonts supported for thermal printing."""
    return SUPPORTED_FONT_NAMES


def supported_fonts_help() -> str:
    """Return a human-readable list of limited public font choices."""
    rows = ['Supported ASCII art fonts for 80mm / 48-column receipts:', '']
    for name in SUPPORTED_FONT_NAMES:
        meta = ASCII_FONT_CATALOG[name]
        rows.append(
            f"- {name}: {meta['style']}, hint {meta['max_chars_hint']} chars; "
            f"best for {meta['best_for']}."
        )
    rows.extend([
        '',
        'These are the public font choices for --ascii-font and markdown fences.',
        'Printime still measures rendered width and wraps words automatically.',
        'Compact fallback fonts are internal only when a requested font is too wide.',
    ])
    return '\n'.join(rows)


def _normalize_text(text: str) -> str:
    return ' '.join(
        line.strip() for line in text.splitlines() if line.strip()
    ).strip()


def _font_chain(font: str) -> list[str]:
    normalized = font.strip().lower() or 'slant'
    fallbacks = FONT_FALLBACKS.get(normalized, ('small', 'smslant', 'mini'))
    return [normalized, *[f for f in fallbacks if f != normalized]]


def _api_font_name(font: str) -> str:
    """Map public CLI font names to asciified API font names."""
    return API_FONT_NAMES.get(font.strip().lower(), font)


def _clean_render_lines(lines: list[str]) -> list[str]:
    return [line.rstrip() for line in lines if line.rstrip()]


def _render_pyfiglet(text: str, font: str) -> list[str]:
    try:
        pyfiglet = importlib.import_module('pyfiglet')
    except ImportError as exc:
        raise AsciiArtError('pyfiglet is not installed') from exc

    rendered = pyfiglet.Figlet(
        font=font,
        width=200,
    ).renderText(text)
    return _clean_render_lines(rendered.splitlines())


def _render_api(text: str, font: str) -> list[str]:
    from urllib.parse import urlencode
    from urllib.request import urlopen

    api_font = _api_font_name(font)
    query = urlencode({'text': text, 'font': api_font})
    url = f'https://asciified.thelicato.io/api/v2/ascii?{query}'
    with urlopen(url, timeout=8) as response:
        body = response.read().decode('utf-8', errors='replace')
    return _clean_render_lines(body.splitlines())


def _fits(lines: list[str], width: int) -> bool:
    return bool(lines) and all(len(line) <= width for line in lines)


def _split_word_to_fit(
    word: str,
    font: str,
    width: int,
    render: Callable[[str, str], list[str]],
) -> tuple[list[str], list[str]]:
    chunks: list[str] = []
    all_lines: list[str] = []
    current = ''

    for char in word:
        candidate = f'{current}{char}'
        candidate_lines = render(candidate, font)
        if _fits(candidate_lines, width):
            current = candidate
            continue
        if not current:
            raise AsciiArtError(
                f"'{char}' does not fit {width} columns with font '{font}'"
            )
        lines = render(current, font)
        chunks.append(current)
        all_lines.extend(lines)
        current = char
        if not _fits(render(current, font), width):
            raise AsciiArtError(
                f"'{char}' does not fit {width} columns with font '{font}'"
            )

    if current:
        lines = render(current, font)
        chunks.append(current)
        all_lines.extend(lines)

    return chunks, all_lines


def _align_lines(lines: list[str], width: int, align: str) -> list[str]:
    if align == 'center':
        return [line.center(width).rstrip() for line in lines]
    if align == 'right':
        return [line.rjust(width) for line in lines]
    return lines


def _wrap_words(
    text: str,
    font: str,
    width: int,
    render: Callable[[str, str], list[str]],
) -> tuple[list[str], list[str]]:
    words = text.split()
    chunks: list[str] = []
    all_lines: list[str] = []
    current = ''

    for word in words:
        candidate = f'{current} {word}'.strip()
        candidate_lines = render(candidate, font)
        if _fits(candidate_lines, width):
            current = candidate
            continue

        if current:
            lines = render(current, font)
            chunks.append(current)
            all_lines.extend(lines)
            current = word
            word_lines = render(word, font)
            if not _fits(word_lines, width):
                split_chunks, split_lines = _split_word_to_fit(
                    word, font, width, render,
                )
                chunks.extend(split_chunks)
                all_lines.extend(split_lines)
                current = ''
            continue

        split_chunks, split_lines = _split_word_to_fit(word, font, width, render)
        chunks.extend(split_chunks)
        all_lines.extend(split_lines)

    if current:
        lines = render(current, font)
        if not _fits(lines, width):
            raise AsciiArtError(
                f"'{current}' does not fit {width} columns with font '{font}'"
            )
        chunks.append(current)
        all_lines.extend(lines)

    return chunks, all_lines


def render_ascii_art(
    text: str,
    *,
    font: str = 'slant',
    width: int = 48,
    align: str = 'left',
    api_fallback: bool = False,
    strict: bool = False,
) -> AsciiArtResult:
    """Render text as ASCII art, wrapping by measured output width."""
    plain = _normalize_text(text)
    if not plain:
        return AsciiArtResult('', font, [], [], [])

    requested = font.strip().lower() or 'slant'
    if requested not in SAFE_FONTS:
        supported = ', '.join(SUPPORTED_FONT_NAMES)
        raise AsciiArtError(
            f"Unsupported ASCII art font '{requested}'. Supported fonts: {supported}"
        )
    if requested in DISCOURAGED_FONTS:
        raise AsciiArtError(
            f"Font '{requested}' is not recommended for thermal printing"
        )

    warnings: list[str] = []
    failures: list[str] = []
    renderers: list[Callable[[str, str], list[str]]] = [_render_pyfiglet]
    if api_fallback:
        renderers.append(_render_api)

    for candidate in _font_chain(requested):
        for render in renderers:
            try:
                chunks, lines = _wrap_words(plain, candidate, width, render)
            except Exception as exc:
                failures.append(str(exc))
                continue
            if candidate != requested:
                message = (
                    f"Font '{requested}' was too wide; used '{candidate}' instead"
                )
                if strict:
                    raise AsciiArtError(message)
                warnings.append(message)
            return AsciiArtResult(
                plain_text=plain,
                font=candidate,
                lines=_align_lines(lines, width, align),
                chunks=chunks,
                warnings=warnings,
            )

    message = '; '.join(failures) or (
        f"Could not render '{plain}' within {width} columns"
    )
    raise AsciiArtError(message)
