#!/usr/bin/env python3
"""Split markdown into ordered print segments (text, checklist, mermaid, QR)."""

from __future__ import annotations

import re
import shlex
from typing import Any, Dict, List, Tuple

FENCED_BLOCK_RE = re.compile(
    r'```\s*(mermaid|qr)([^\n]*)\r?\n(.*?)```',
    re.DOTALL | re.IGNORECASE,
)

FENCE_RE = re.compile(
    r'```([^\n]*)\r?\n(.*?)```',
    re.DOTALL,
)

MERMAID_START_RE = re.compile(
    r'^\s*(?:graph\s+(?:TD|TB|BT|RL|LR)|flowchart|sequenceDiagram|classDiagram|'
    r'stateDiagram-v?\d*|erDiagram|journey|gantt|pie(?:\s|$)|gitGraph|mindmap|'
    r'timeline|quadrantChart|sankey-beta|xychart-beta|block-beta)\b',
    re.IGNORECASE | re.MULTILINE,
)

QR_SIZE_MIN = 4
QR_SIZE_MAX = 12
QR_SIZE_DEFAULT = 8


def parse_qr_fence_options(header: str) -> Dict[str, Any]:
    """Parse ```qr fence flags (same names as printime print --qr)."""
    options: Dict[str, Any] = {}
    header = header.strip()
    if not header:
        return options

    try:
        tokens = shlex.split(header)
    except ValueError:
        tokens = header.split()

    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token == '--':
            idx += 1
            continue
        if token in ('--qr-size', '--qr_size') and idx + 1 < len(tokens):
            size = int(tokens[idx + 1])
            options['qr_size'] = max(QR_SIZE_MIN, min(QR_SIZE_MAX, size))
            idx += 2
            continue
        if token == '--show-link':
            options['show_link'] = True
            idx += 1
            continue
        if token == '--center':
            options['center'] = True
            idx += 1
            continue
        idx += 1
    return options


def parse_qr_payload(raw: str) -> str:
    """Parse QR payload from a fenced block body."""
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        return ''
    payload = ' '.join(lines)
    if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in '"\'':
        payload = payload[1:-1]
    else:
        payload = lines[0].strip('"').strip("'")
    return payload.strip()


def normalize_mermaid_source(text: str) -> str:
    """Fix common mermaid corruption from Anytype paste/export."""
    text = text.replace('\u2014>', '-->').replace('—>', '-->').replace('→', '-->')
    text = re.sub(
        r'(\])\s*([A-Za-z][A-Za-z0-9_]*(?:\s*(?:-->|—>|→)|\[|\())',
        r'\1\n\2',
        text,
    )
    return text.strip()


def _looks_like_mermaid(text: str) -> bool:
    return bool(MERMAID_START_RE.search(text.strip()))


def _classify_fence(header: str, payload: str) -> Tuple[str, str, str]:
    """Map a fenced block to segment kind (markdown, mermaid, qr)."""
    header = header.strip()
    lower = header.lower()
    if lower == 'mermaid' or lower.startswith('mermaid '):
        opts = header.split(None, 1)[1] if ' ' in header else ''
        return 'mermaid', payload, opts
    if lower == 'qr' or (lower.startswith('qr') and (len(header) <= 2 or header[2] in ' \t-')):
        opts = header[2:].strip() if len(header) > 2 else ''
        return 'qr', payload, opts
    if not header and _looks_like_mermaid(payload):
        return 'mermaid', payload, ''
    wrapped = f'```{header}\n{payload}```' if header else f'```\n{payload}```'
    return 'markdown', wrapped, ''


def split_markdown_body(body: str) -> List[Tuple[str, str, str]]:
    """Return ordered (kind, payload, fence_header) triples."""
    parts: List[Tuple[str, str, str]] = []
    pos = 0
    for match in FENCE_RE.finditer(body):
        if match.start() > pos:
            parts.append(('markdown', body[pos:match.start()], ''))
        kind, payload, header = _classify_fence(match.group(1), match.group(2))
        parts.append((kind, payload, header))
        pos = match.end()
    if pos < len(body):
        parts.append(('markdown', body[pos:], ''))
    if not parts:
        parts.append(('markdown', body, ''))
    return parts


def _markdown_chunk_to_segments(text: str, width: int) -> List[Dict[str, Any]]:
    """Split a markdown chunk into styled text and checklist segments in source order."""
    from printime.styled import lines_to_plain_preview, markdown_to_print_lines

    segments: List[Dict[str, Any]] = []
    prose_lines: List[str] = []
    item_buffer: List[Dict[str, Any]] = []

    def flush_prose() -> None:
        chunk = '\n'.join(prose_lines).strip()
        prose_lines.clear()
        if not chunk:
            return
        lines = markdown_to_print_lines(chunk, width)
        segments.append({
            'type': 'styled',
            'lines': lines,
            'preview': lines_to_plain_preview(lines, width),
        })

    def flush_items() -> None:
        if not item_buffer:
            return
        segments.append({'type': 'items', 'items': list(item_buffer)})
        item_buffer.clear()

    for line in text.splitlines():
        match = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', line)
        if match:
            flush_prose()
            label = match.group(2).strip()
            if label:
                item_buffer.append({
                    'text': label,
                    'checked': match.group(1).lower() == 'x',
                })
            continue
        if item_buffer:
            flush_items()
        prose_lines.append(line)

    flush_prose()
    flush_items()
    return segments


def build_print_segments(
    body: str,
    width: int = 48,
    *,
    link_qr: bool = False,
    link_qr_size: int = 5,
    main_url: str | None = None,
) -> List[Dict[str, Any]]:
    """Build ordered segments for thermal printing."""
    segments: List[Dict[str, Any]] = []
    for kind, payload, header in split_markdown_body(body):
        if kind == 'markdown':
            if link_qr:
                from printime.services.link_qr import markdown_lines_to_link_segments
                segments.extend(
                    markdown_lines_to_link_segments(
                        payload, width, link_qr_size=link_qr_size, main_url=main_url,
                    )
                )
            else:
                segments.extend(_markdown_chunk_to_segments(payload, width))
        elif kind == 'mermaid':
            source = normalize_mermaid_source(payload)
            if source:
                segments.append({'type': 'mermaid', 'source': source})
        elif kind == 'qr':
            data = parse_qr_payload(payload)
            if data:
                segment: Dict[str, Any] = {'type': 'qr', 'data': data}
                segment.update(parse_qr_fence_options(header))
                segments.append(segment)
    return segments


def should_use_segment_print(segments: List[Dict[str, Any]], template_name: str) -> bool:
    """Whether ordered segment printing/preview is required."""
    if not segments:
        return False
    kinds = {seg.get('type') for seg in segments}
    if kinds == {'mermaid'} and template_name == 'diagram':
        return False
    if template_name in ('document', 'ticket'):
        return True
    if kinds & {'qr', 'barcode', 'code_image'}:
        return True
    if len(segments) > 1:
        return True
    return False
