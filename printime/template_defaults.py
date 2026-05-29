#!/usr/bin/env python3
"""Default slip titles when --title is omitted."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

# Printed header when --title is not provided (template name, title-cased).
TEMPLATE_DEFAULT_TITLES: Dict[str, str] = {
    'note': 'Note',
    'checklist': 'Checklist',
    'task': 'Task',
    'message': 'Message',
    'email': 'Email',
    'jira': 'Jira',
    'document': 'Document',
    'receipt': 'Receipt',
    'heading': 'Heading',
    'agenda': 'Agenda',
    'ticket': 'Ticket',
    'diagram': 'Diagram',
    'equation': 'Equation',
}

INTENT_DEFAULT_TITLES: Dict[str, str] = {
    'note': TEMPLATE_DEFAULT_TITLES['note'],
    'checklist': TEMPLATE_DEFAULT_TITLES['checklist'],
    'task': TEMPLATE_DEFAULT_TITLES['task'],
    'message': TEMPLATE_DEFAULT_TITLES['message'],
    'email': TEMPLATE_DEFAULT_TITLES['email'],
}


def default_title_for_template(template: Optional[str]) -> Optional[str]:
    if not template:
        return None
    return TEMPLATE_DEFAULT_TITLES.get(template.lower())


def default_title_for_intent(intent: Optional[str]) -> Optional[str]:
    if not intent:
        return None
    return INTENT_DEFAULT_TITLES.get(intent.lower())


def ensure_template_title(context: dict, template: Optional[str]) -> dict:
    """Set context title to the template default when --title was omitted."""
    if context.get('title') or not template:
        return context
    default = default_title_for_template(template)
    if not default:
        return context
    updated = dict(context)
    updated['title'] = default
    return updated


def strip_default_title_flag(argv: Sequence[str]) -> list[str]:
    """Remove --title when it equals the intent's template default (for eval matching)."""
    tokens = list(argv)
    if len(tokens) < 2:
        return tokens
    intent = tokens[1]
    default = default_title_for_intent(intent)
    if not default:
        return tokens
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '--title' and i + 1 < len(tokens) and tokens[i + 1] == default:
            i += 2
            continue
        out.append(tokens[i])
        i += 1
    return out
