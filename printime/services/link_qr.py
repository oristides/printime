#!/usr/bin/env python3
"""Turn URLs in text/markdown into mini QR print segments."""

from __future__ import annotations

import html as html_module
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

URL_RE = re.compile(r'https?://[^\s<>\]\)\"\'\]]+', re.IGNORECASE)
MD_LINK_RE = re.compile(r'\[([^\]]*)\]\((https?://[^\)]+)\)')
AUTOLINK_RE = re.compile(r'<(https?://[^>\s]+)>')
HTML_ANCHOR_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

DEFAULT_LINK_QR_SIZE = 4
DEFAULT_LINK_QR_ALIGN = 'left'
LINK_QR_SIZE_MIN = 3
LINK_QR_SIZE_MAX = 8


def is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False


def link_qr_settings_from_config(config: Dict[str, Any] | None) -> Tuple[int, str]:
    """Read mini QR size/align from printer config."""
    printer = (config or {}).get('printer', {})
    size = int(printer.get('link_qr_size', DEFAULT_LINK_QR_SIZE))
    size = max(LINK_QR_SIZE_MIN, min(LINK_QR_SIZE_MAX, size))
    align = str(printer.get('link_qr_align', DEFAULT_LINK_QR_ALIGN)).lower()
    if align not in ('left', 'center', 'right'):
        align = DEFAULT_LINK_QR_ALIGN
    return size, align


def link_qr_kwargs_from_config(config: Dict[str, Any] | None) -> Dict[str, Any]:
    size, align = link_qr_settings_from_config(config)
    return {
        'link_qr': True,
        'link_qr_size': size,
        'link_qr_align': align,
    }


def _link_label(url: str, inner_text: str) -> str:
    label = re.sub(r'\s+', ' ', inner_text).strip()
    if label:
        return label
    host = urlparse(url).netloc.removeprefix('www.')
    return host or url


def normalize_document_links(text: str) -> str:
    """Normalize HTML anchors and autolinks to markdown [label](url)."""
    def anchor_repl(match: re.Match[str]) -> str:
        url = html_module.unescape(match.group(1)).strip()
        if not is_http_url(url):
            return match.group(0)
        inner = re.sub(r'<[^>]+>', ' ', match.group(2))
        inner = html_module.unescape(inner)
        label = _link_label(url, inner)
        return f' [{label}]({url}) '

    text = HTML_ANCHOR_RE.sub(anchor_repl, text)

    def autolink_repl(match: re.Match[str]) -> str:
        url = match.group(1).strip()
        label = _link_label(url, '')
        return f' [{label}]({url}) '

    return AUTOLINK_RE.sub(autolink_repl, text)


def make_link_qr_segment(
    url: str,
    *,
    link_qr_size: int = DEFAULT_LINK_QR_SIZE,
    link_qr_align: str = DEFAULT_LINK_QR_ALIGN,
    main_url: bool = False,
) -> Dict[str, Any]:
    """Build one mini (or main) link QR segment."""
    if main_url:
        return {
            'type': 'qr',
            'data': url,
            'qr_size': max(link_qr_size + 2, 7),
            'center': True,
            'align': 'center',
            'link_qr': True,
            'main_url': True,
        }
    return {
        'type': 'qr',
        'data': url,
        'qr_size': link_qr_size,
        'center': link_qr_align == 'center',
        'align': link_qr_align,
        'link_qr': True,
    }


def extract_markdown_links(line: str) -> List[Tuple[str, str, int, int]]:
    """Return (label, url, start, end) for markdown links on a line."""
    return [
        (m.group(1).strip(), m.group(2).strip(), m.start(), m.end())
        for m in MD_LINK_RE.finditer(line)
    ]


def markdown_lines_to_link_segments(
    body: str,
    width: int = 48,
    *,
    link_qr_size: int = DEFAULT_LINK_QR_SIZE,
    link_qr_align: str = DEFAULT_LINK_QR_ALIGN,
    main_url: str | None = None,
) -> List[Dict[str, Any]]:
    """Parse markdown body into styled + optional link QR segments in order."""
    from printime.services.markdown_blocks import _markdown_chunk_to_segments

    segments: List[Dict[str, Any]] = []
    prose_lines: List[str] = []

    def flush_prose() -> None:
        chunk = '\n'.join(prose_lines).strip()
        prose_lines.clear()
        if chunk:
            segments.extend(_markdown_chunk_to_segments(chunk, width))

    for line in body.splitlines():
        links = extract_markdown_links(line)
        if not links:
            prose_lines.append(line)
            continue
        flush_prose()
        pos = 0
        for label, url, start, end in links:
            before = line[pos:start].strip()
            if before:
                segments.extend(_markdown_chunk_to_segments(before, width))
            if label:
                segments.extend(_markdown_chunk_to_segments(label, width))
            segments.append(
                make_link_qr_segment(
                    url,
                    link_qr_size=link_qr_size,
                    link_qr_align=link_qr_align,
                )
            )
            pos = end
        tail = line[pos:].strip()
        if tail:
            prose_lines.append(tail)

    flush_prose()

    if main_url and is_http_url(main_url):
        segments.append(
            make_link_qr_segment(
                main_url,
                link_qr_size=link_qr_size,
                link_qr_align=link_qr_align,
                main_url=True,
            )
        )

    return segments


def append_bare_url_qrs(
    segments: List[Dict[str, Any]],
    text: str,
    *,
    link_qr_size: int = DEFAULT_LINK_QR_SIZE,
    link_qr_align: str = DEFAULT_LINK_QR_ALIGN,
) -> List[Dict[str, Any]]:
    """Add mini QRs for bare URLs not already covered by link segments."""
    existing = {seg.get('data') for seg in segments if seg.get('type') == 'qr'}
    out = list(segments)
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip('.,;:)')
        if url in existing:
            continue
        existing.add(url)
        out.append(
            make_link_qr_segment(
                url,
                link_qr_size=link_qr_size,
                link_qr_align=link_qr_align,
            )
        )
    return out
