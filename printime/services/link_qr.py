#!/usr/bin/env python3
"""Turn URLs in text/markdown into mini QR print segments."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

URL_RE = re.compile(r'https?://[^\s<>\]\)\"\'\]]+', re.IGNORECASE)
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
DEFAULT_LINK_QR_SIZE = 5


def is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False


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
            segments.extend(_markdown_chunk_to_segments(label, width))
            segments.append({
                'type': 'qr',
                'data': url,
                'qr_size': link_qr_size,
                'center': True,
                'link_qr': True,
            })
            pos = end
        tail = line[pos:].strip()
        if tail:
            prose_lines.append(tail)

    flush_prose()

    if main_url and is_http_url(main_url):
        segments.append({
            'type': 'qr',
            'data': main_url,
            'qr_size': max(link_qr_size + 2, 7),
            'center': True,
            'link_qr': True,
            'main_url': True,
        })

    return segments


def append_bare_url_qrs(
    segments: List[Dict[str, Any]],
    text: str,
    *,
    link_qr_size: int = DEFAULT_LINK_QR_SIZE,
) -> List[Dict[str, Any]]:
    """Add mini QRs for bare URLs not already covered by link segments."""
    existing = {seg.get('data') for seg in segments if seg.get('type') == 'qr'}
    out = list(segments)
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip('.,;:)')
        if url in existing:
            continue
        existing.add(url)
        out.append({
            'type': 'qr',
            'data': url,
            'qr_size': link_qr_size,
            'center': True,
            'link_qr': True,
        })
    return out
