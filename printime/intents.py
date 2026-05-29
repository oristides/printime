#!/usr/bin/env python3
"""Intent-first CLI commands: preview by default, --print to paper."""

from __future__ import annotations

import argparse
from typing import Any, Dict, Optional

INTENT_COMMANDS = (
    'note',
    'checklist',
    'task',
    'message',
    'email',
    'url',
    'qr',
    'ticket',
    'image',
    'ascii',
)

INTENT_SPECS: Dict[str, Dict[str, Any]] = {
    'note': {'template': 'note', 'kind': 'template'},
    'checklist': {'template': 'checklist', 'kind': 'template'},
    'task': {'template': 'task', 'kind': 'template'},
    'message': {'template': 'message', 'kind': 'template'},
    'email': {'template': 'email', 'kind': 'template'},
    'url': {'kind': 'url'},
    'qr': {'kind': 'qr'},
    'ticket': {'kind': 'ticket', 'template': 'ticket'},
    'image': {'kind': 'image'},
    'ascii': {'kind': 'ascii'},
}

PREVIEW_HINT = 'Preview only. Add --print to send to paper.'


def _apply_eval_safety_mode(args) -> None:
    """When PRINTIME_EVAL=1, never send jobs to paper (eval harness only)."""
    import os

    if not os.environ.get('PRINTIME_EVAL'):
        return
    if hasattr(args, 'print'):
        args.print = False
    args.preview = True
    args.yes = False


def apply_intent_output_mode(args) -> None:
    """Intent commands preview by default; --print sends to the printer."""
    _apply_eval_safety_mode(args)
    if getattr(args, 'print', False):
        args.preview = False
        args.yes = True
    else:
        args.preview = True
        args.yes = False


def apply_body_fields(args) -> None:
    """Map --body to internal content field."""
    from printime.text_encoding import decode_cli_escapes

    body = getattr(args, 'body', None)
    if body and not getattr(args, 'content', None):
        args.content = decode_cli_escapes(body)


def add_intent_output_args(parser) -> None:
    parser.add_argument(
        '--print',
        action='store_true',
        help='Send to printer (default: terminal preview only)',
    )
    parser.add_argument('--no-cut', action='store_true', help='Do not cut paper')


def add_template_intent_args(
    parser,
    *,
    intent: str,
    with_items: bool = False,
    with_task: bool = False,
) -> None:
    from printime.template_defaults import INTENT_DEFAULT_TITLES

    default_title = INTENT_DEFAULT_TITLES.get(intent, 'Note')
    parser.add_argument(
        '--title',
        help=f'Slip header (optional; default: {default_title})',
    )
    if intent == 'checklist':
        parser.add_argument(
            '--body',
            help='Optional intro text above the list (address, notes, …)',
        )
    else:
        parser.add_argument('--body', help='Main text on the slip')
    parser.add_argument('--caption', help='Subtitle under the title')
    parser.add_argument('--file', '-f', help='Context file (.md, .json, .yaml)')
    parser.add_argument('--priority', help='Priority (HIGH, MEDIUM, LOW)')
    parser.add_argument('--tags', help='Tags (comma-separated)')
    parser.add_argument('--content', help=argparse.SUPPRESS)
    parser.add_argument('--item', action='append', help=argparse.SUPPRESS)
    if with_items:
        parser.add_argument(
            '--items',
            metavar='LIST',
            help='Checkbox list, pipe-separated: Milk|Bread::done (checked: ::done or ::checked)',
        )
    if with_task:
        parser.add_argument('--due', help='Due date (YYYY-MM-DD)')
        parser.add_argument(
            '--done',
            action='store_true',
            help='Mark task completed',
        )


def register_intent_parsers(subparsers, registry: dict) -> None:
    """Register intent subcommands on the root parser."""
    from printime.cli_epilog import INTENT_EPILOGS
    from printime.cli_help import HelpfulArgumentParser
    from printime.services.ascii_art import supported_font_names

    help_lines = {
        'note': 'Quick memo (--body; --title optional, default Note)',
        'checklist': 'Todo list (--items; optional --body/--caption; default title Checklist)',
        'task': 'Single task card (--body; --title optional, default Task)',
        'message': 'Short alert (--body; --title optional, default Message)',
        'email': 'Email summary (--body; --title optional, default Email)',
        'url': 'Print a web article (not QR)',
        'qr': 'Standalone QR code (not full article)',
        'ticket': 'Ticket PDF (QR/barcodes)',
        'image': 'PNG/JPG image',
        'ascii': 'ASCII art banner',
    }

    for name in INTENT_COMMANDS:
        spec = INTENT_SPECS[name]
        kind = spec['kind']
        p = subparsers.add_parser(
            name,
            help=help_lines[name],
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=INTENT_EPILOGS.get(name, ''),
        )
        registry[name] = p
        p.set_defaults(command=name, intent=name)
        add_intent_output_args(p)

        if kind == 'template':
            add_template_intent_args(
                p,
                intent=name,
                with_items=(name == 'checklist'),
                with_task=(name == 'task'),
            )
            if name == 'task' and '--done' in [a.dest for a in p._actions]:
                pass
        elif kind == 'url':
            p.add_argument('target', help='Article URL')
            p.add_argument('--max-chars', type=int, default=12000,
                           help='Max characters (0 = no limit)')
            p.add_argument('--link-qr', action='store_true',
                           help='Add mini QR codes for URLs in article')
        elif kind == 'qr':
            p.add_argument('target', help='QR payload (URL, text, etc.)')
            p.add_argument('--qr-size', type=int, default=8,
                           help='Module size 4-12 (default 8)')
            p.add_argument('--show-link', action='store_true',
                           help='Print URL text below QR')
        elif kind == 'ticket':
            p.add_argument('target', help='Ticket PDF path')
        elif kind == 'image':
            p.add_argument('target', help='PNG/JPG path')
            p.add_argument('--title', help='Optional title')
            p.add_argument('--caption', help='Optional caption')
        elif kind == 'ascii':
            p.add_argument('target', help='Text to render as ASCII art')
            p.add_argument('--ascii-font', choices=supported_font_names(), default='slant')
            p.add_argument('--center', action='store_true')
            p.add_argument('--ascii-api-fallback', action='store_true')
            p.add_argument('--ascii-strict', action='store_true')


def build_template_context(args, config: dict) -> dict:
    """Build template context from intent args."""
    spec = INTENT_SPECS.get(getattr(args, 'intent', ''), {})
    if spec.get('template'):
        args.template = spec['template']
    context: dict = {}
    if getattr(args, 'file', None):
        from printime.cli import load_context_file
        context = load_context_file(args.file)
    else:
        if getattr(args, 'title', None):
            context['title'] = args.title
        if getattr(args, 'caption', None):
            context['caption'] = args.caption
        apply_body_fields(args)
        if getattr(args, 'content', None):
            context['content'] = args.content
        if getattr(args, 'priority', None):
            context['priority'] = args.priority
        if getattr(args, 'tags', None):
            context['tags'] = [t.strip() for t in args.tags.split(',')]
        if getattr(args, 'due', None):
            context['due_date'] = args.due
        if getattr(args, 'done', False):
            context['completed'] = True

    from printime.cli import _finalize_template_context
    return _finalize_template_context(context, args, config)


def _synthetic_print_args(args, **overrides):
    """Build a Namespace compatible with cmd_print branches."""
    from argparse import Namespace

    base = dict(
        test=None,
        template=getattr(args, 'template', None),
        title=getattr(args, 'title', None),
        body=getattr(args, 'body', None),
        content=getattr(args, 'content', None),
        items=getattr(args, 'items', None),
        item=getattr(args, 'item', None),
        file=getattr(args, 'file', None),
        md=None,
        text=None,
        url=getattr(args, 'url', None),
        qr=getattr(args, 'qr', None),
        ticket=getattr(args, 'ticket', None),
        image=getattr(args, 'image', None),
        mermaid=None,
        ascii=getattr(args, 'ascii', None),
        preview=getattr(args, 'preview', True),
        yes=getattr(args, 'yes', False),
        no_cut=getattr(args, 'no_cut', False),
        priority=getattr(args, 'priority', None),
        tags=getattr(args, 'tags', None),
        due=getattr(args, 'due', None),
        done=getattr(args, 'done', False),
        qr_size=getattr(args, 'qr_size', 8),
        show_link=getattr(args, 'show_link', False),
        link_qr=getattr(args, 'link_qr', False),
        max_chars=getattr(args, 'max_chars', 12000),
        bold=False,
        center=getattr(args, 'center', False),
        double_height=False,
        ascii_font=getattr(args, 'ascii_font', 'slant'),
        ascii_api_fallback=getattr(args, 'ascii_api_fallback', False),
        ascii_strict=getattr(args, 'ascii_strict', False),
        markdown=False,
        input=None,
    )
    base.update(overrides)
    return Namespace(**base)


def cmd_intent(args, config: dict, printer) -> None:
    """Dispatch an intent subcommand."""
    from printime.cli import cmd_print

    apply_intent_output_mode(args)
    apply_body_fields(args)
    spec = INTENT_SPECS[args.intent]
    kind = spec['kind']

    if kind == 'template':
        cmd_print(_synthetic_print_args(args, template=spec['template']), config, printer)
        return

    if kind == 'url':
        cmd_print(_synthetic_print_args(
            args, url=args.target, link_qr=getattr(args, 'link_qr', False),
        ), config, printer)
        return

    if kind == 'qr':
        cmd_print(_synthetic_print_args(
            args, qr=args.target,
        ), config, printer)
        return

    if kind == 'ticket':
        cmd_print(_synthetic_print_args(args, ticket=args.target), config, printer)
        return

    if kind == 'image':
        cmd_print(_synthetic_print_args(args, image=args.target), config, printer)
        return

    if kind == 'ascii':
        cmd_print(_synthetic_print_args(
            args, ascii=args.target,
        ), config, printer)
        return

    raise ValueError(f'Unknown intent kind: {kind}')


def is_intent_command(command: Optional[str]) -> bool:
    return command in INTENT_SPECS
