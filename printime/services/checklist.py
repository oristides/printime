#!/usr/bin/env python3
"""Checklist item parsing and context enrichment for CLI and templates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

_CHECKED_SUFFIXES = frozenset({'checked', 'x', 'done'})
ITEMS_SEPARATOR = '|'


def parse_checklist_item(raw: str) -> Dict[str, Any]:
    """Parse one ``--item`` value.

    Unchecked: ``Milk``
    Checked: ``Bread::done``, ``Bread::checked`` (legacy: ``Bread::x``)

    Uses ``::`` so item text may contain single colons (``Deploy: staging``).
    Only a recognized suffix after the final ``::`` marks an item checked.
    """
    text = raw.strip()
    if not text:
        raise ValueError('checklist item cannot be empty')
    if '::' in text:
        label, suffix = text.rsplit('::', 1)
        label = label.strip()
        flag = suffix.strip().lower()
        if flag in _CHECKED_SUFFIXES:
            if not label:
                raise ValueError('checklist item text cannot be empty')
            return {'text': label, 'checked': True}
    return {'text': text, 'checked': False}


def parse_checklist_items(raw_items: Sequence[str]) -> List[Dict[str, Any]]:
    return [parse_checklist_item(item) for item in raw_items]


def parse_checklist_items_string(raw: str) -> List[Dict[str, Any]]:
    """Parse one ``--items`` value: ``Milk|Bread::x|Deploy: staging``."""
    if not raw.strip():
        raise ValueError('checklist items cannot be empty')
    parts = [part.strip() for part in raw.split(ITEMS_SEPARATOR)]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError('checklist items cannot be empty')
    return parse_checklist_items(parts)


def collect_cli_checklist_items(
    *,
    items_string: Optional[str] = None,
    item_flags: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Merge ``--items`` and optional repeated ``--item`` flags."""
    collected: List[Dict[str, Any]] = []
    if items_string:
        collected.extend(parse_checklist_items_string(items_string))
    if item_flags:
        collected.extend(parse_checklist_items(item_flags))
    return collected


def _set_prose_content(context: Dict[str, Any], prose: str, width: int) -> None:
    from printime.styled import lines_to_plain_preview, markdown_to_print_lines

    context['content_lines'] = markdown_to_print_lines(prose, width)
    context['content'] = lines_to_plain_preview(context['content_lines'], width)


def enrich_checklist_context(
    context: Dict[str, Any],
    *,
    template: Optional[str],
    cli_items: Optional[Sequence[str]] = None,
    cli_items_string: Optional[str] = None,
    width: int = 48,
) -> Dict[str, Any]:
    """Apply ``--items`` / ``--item`` flags and checklist content parsing."""
    has_cli_items = bool(cli_items or cli_items_string)
    if template != 'checklist' and not has_cli_items:
        return context

    ctx = dict(context)
    items: List[Dict[str, Any]] = list(ctx.get('items') or [])

    if has_cli_items:
        try:
            items.extend(collect_cli_checklist_items(
                items_string=cli_items_string,
                item_flags=cli_items,
            ))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    content = ctx.get('content')
    if isinstance(content, str) and content.strip():
        from printime.services.transform import _parse_checkboxes

        parsed, remaining = _parse_checkboxes(content)
        if parsed:
            items.extend(parsed)
        remaining = remaining.strip()
        if remaining:
            _set_prose_content(ctx, remaining, width)
        else:
            ctx.pop('content', None)
            ctx.pop('content_lines', None)

    if items:
        ctx['items'] = items

    return ctx
