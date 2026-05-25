#!/usr/bin/env python3
"""Google Keep integration via gkeepapi (unofficial; personal Gmail accounts)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

KEEP_URL_RE = re.compile(r'#NOTE/([^/?#]+)')
KEEP_NOTE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{20,}$')


def parse_note_id(url_or_id: str) -> str:
    """Extract Keep note ID from a share URL or raw ID."""
    value = url_or_id.strip()
    match = KEEP_URL_RE.search(value)
    if match:
        return match.group(1)
    if 'keep.google.com' in value:
        tail = value.rsplit('/', 1)[-1]
        if KEEP_NOTE_ID_RE.match(tail):
            return tail
    return value


def get_keep_config() -> Dict[str, Optional[str]]:
    from printime.config import load_env

    load_env()
    return {
        'email': os.getenv('GOOGLE_KEEP_EMAIL'),
        'master_token': os.getenv('GOOGLE_KEEP_MASTER_TOKEN'),
        'state_path': os.getenv('GOOGLE_KEEP_STATE_PATH'),
    }


def _require_gkeepapi():
    try:
        import gkeepapi  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            'Google Keep support requires gkeepapi. Install with:\n'
            '  pipx inject printime gkeepapi\n'
            '  # or: pip install printime[keep]'
        ) from exc


def connect_keep(*, email: str | None = None, master_token: str | None = None):
    """Authenticate to Google Keep and sync notes."""
    _require_gkeepapi()
    import gkeepapi

    cfg = get_keep_config()
    email = email or cfg.get('email')
    master_token = master_token or cfg.get('master_token')
    if not email or not master_token:
        raise ValueError(
            'Set GOOGLE_KEEP_EMAIL and GOOGLE_KEEP_MASTER_TOKEN in .env\n'
            'See docs/KEEP.md for how to obtain a master token.'
        )

    keep = gkeepapi.Keep()
    state = None
    state_path = cfg.get('state_path')
    if state_path:
        state_path = os.path.expanduser(state_path)
    if state_path and os.path.isfile(state_path):
        import json

        with open(state_path, 'r', encoding='utf-8') as fh:
            state = json.load(fh)

    if not keep.authenticate(email, master_token, state=state):
        raise ValueError('Google Keep authentication failed — check email and master token')

    keep.sync()

    if state_path:
        import json

        parent = os.path.dirname(os.path.abspath(state_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as fh:
            json.dump(keep.dump(), fh)

    return keep


def note_to_markdown(note) -> str:
    """Convert a Keep note/list to markdown for printime."""
    parts: List[str] = []
    title = (getattr(note, 'title', None) or '').strip()
    if title:
        parts.append(f'# {title}')

    items = getattr(note, 'items', None)
    if items:
        for item in items:
            text = (getattr(item, 'text', None) or '').strip()
            if not text:
                continue
            mark = 'x' if getattr(item, 'checked', False) else ' '
            parts.append(f'- [{mark}] {text}')
    else:
        body = (getattr(note, 'text', None) or '').strip()
        if body:
            parts.append(body)

    labels = getattr(note, 'labels', None)
    if labels:
        try:
            names = [lb.name for lb in labels.all() if getattr(lb, 'name', None)]
        except Exception:
            names = []
        if names:
            parts.append('')
            parts.append('Labels: ' + ', '.join(names))

    return '\n\n'.join(parts).strip()


def find_note(keep, url_or_id: str):
    """Resolve a note by URL/id or title search."""
    note_id = parse_note_id(url_or_id)
    note = keep.get(note_id)
    if note:
        return note

    query = url_or_id.strip()
    if query.startswith('http'):
        query = note_id

    hits = list(keep.find(query=query))
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        exact = [n for n in hits if (n.title or '').strip().lower() == query.lower()]
        if len(exact) == 1:
            return exact[0]
        titles = ', '.join(repr(n.title) for n in hits[:5])
        raise ValueError(f'Multiple Keep notes match {query!r}: {titles}')

    raise ValueError(
        f'Keep note not found: {url_or_id!r}\n'
        'Check the URL/id or run: printime keep search "title"'
    )


def note_to_context(
    url_or_id: str,
    width: int = 48,
    config: dict | None = None,
    *,
    keep=None,
) -> Dict[str, Any]:
    """Fetch a Keep note and build printime template context."""
    from printime.services.link_qr import link_qr_kwargs_from_config
    from printime.services.transform import markdown_to_context

    if keep is None:
        keep = connect_keep()
    note = find_note(keep, url_or_id)
    markdown = note_to_markdown(note)
    if not markdown:
        markdown = (note.title or 'Keep note').strip()

    lq = link_qr_kwargs_from_config(config)
    ctx = markdown_to_context(
        markdown,
        note.title or 'Keep note',
        width,
        **lq,
    )
    ctx['title'] = (note.title or ctx.get('title') or 'Keep note').strip()
    ctx['source_url'] = f'https://keep.google.com/#NOTE/{note.id}'
    return ctx


def list_notes(limit: int = 30) -> List[Dict[str, str]]:
    keep = connect_keep()
    rows: List[Dict[str, str]] = []
    for note in keep.all():
        if getattr(note, 'trashed', False) or getattr(note, 'archived', False):
            continue
        rows.append({
            'id': note.id,
            'title': (note.title or '(untitled)').strip(),
            'pinned': 'yes' if getattr(note, 'pinned', False) else '',
        })
    rows.sort(key=lambda r: (r['pinned'] != 'yes', r['title'].lower()))
    return rows[:limit]


def search_notes(query: str, limit: int = 20) -> List[Dict[str, str]]:
    keep = connect_keep()
    return [
        {'id': n.id, 'title': (n.title or '(untitled)').strip()}
        for n in keep.find(query=query)[:limit]
    ]


def print_keep_note(
    url_or_id: str,
    *,
    preview: bool = False,
    yes: bool = False,
    template: str | None = None,
    config: dict | None = None,
) -> bool:
    from printime.cli import _print_template, create_printer, load_config

    if config is None:
        config = load_config()

    keep = connect_keep()
    note = find_note(keep, url_or_id)
    print(f"Keep note: {(note.title or '(untitled)')!r} ({note.id})")

    width = config['printer']['width']
    context = note_to_context(url_or_id, width, config, keep=keep)
    template_name = template or context.get('template', 'document')

    printer = create_printer(config)
    _print_template(
        printer,
        config,
        template_name,
        context,
        preview=preview,
        yes=yes,
        label='Keep',
    )
    return True
