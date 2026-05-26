#!/usr/bin/env python3
"""Enrich plain template fields with markdown and optional link QRs."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

MARKDOWN_HINT = re.compile(
    r'^#{1,6}\s|^\s*[-*+]\s|^\s*-\s*\[[ xX]\]|'
    r'(\*\*.+\*\*)|(\[.+\]\(.+\))|^<center>|```',
    re.MULTILINE | re.IGNORECASE,
)


def looks_like_markdown(text: str) -> bool:
    return bool(text and MARKDOWN_HINT.search(text))


def enrich_context_fields(
    context: Dict[str, Any],
    width: int = 48,
    *,
    markdown: bool = True,
    link_qr: bool = False,
    link_qr_size: int = 5,
    fields: Iterable[str] = ('content', 'description', 'caption'),
) -> Dict[str, Any]:
    """Parse markdown in common text fields into content_lines / segments."""
    from printime.services.markdown_blocks import build_print_segments
    from printime.styled import lines_to_plain_preview, markdown_to_print_lines

    ctx = dict(context)
    if not markdown:
        return ctx

    if ctx.get('segments'):
        return ctx

    combined = ''
    for field in fields:
        val = ctx.get(field)
        if isinstance(val, str) and val.strip():
            combined += f'\n\n{val}'

    if combined.strip():
        segs = build_print_segments(
            combined.strip(),
            width,
            link_qr=link_qr,
            link_qr_size=link_qr_size,
        )
        if segs and any(seg.get('type') != 'styled' for seg in segs):
            ctx['segments'] = segs
            ctx['template'] = ctx.get('template') or 'document'
            return ctx

    for field in fields:
        val = ctx.get(field)
        if not isinstance(val, str) or not val.strip():
            continue
        if not looks_like_markdown(val) and field != 'content':
            continue
        lines = markdown_to_print_lines(val, width)
        ctx[f'{field}_lines'] = lines
        ctx[field] = lines_to_plain_preview(lines, width)

    return ctx
