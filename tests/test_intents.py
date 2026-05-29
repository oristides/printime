"""Tests for intent-first CLI commands (preview by default, --print to paper)."""

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest


class TestIntentOutputMode:
    def test_default_is_preview_only(self):
        from printime.intents import apply_intent_output_mode

        args = Namespace(print=False)
        apply_intent_output_mode(args)
        assert args.preview is True
        assert args.yes is False

    def test_print_flag_sends_to_printer(self):
        from printime.intents import apply_intent_output_mode

        args = Namespace(print=True)
        apply_intent_output_mode(args)
        assert args.preview is False
        assert args.yes is True


class TestBodyMapping:
    def test_body_maps_to_content(self):
        from printime.intents import apply_body_fields

        args = Namespace(body='Votar hoy', content=None)
        apply_body_fields(args)
        assert args.content == 'Votar hoy'

    def test_content_wins_when_both_set(self):
        from printime.intents import apply_body_fields

        args = Namespace(body='ignored', content='keep')
        apply_body_fields(args)
        assert args.content == 'keep'


class TestIntentParser:
    def test_checklist_command_parses(self):
        from printime.cli_parser import create_parser

        parser = create_parser()
        args = parser.parse_args([
            'checklist', '--title', 'Tasks', '--items', 'Votar',
        ])
        assert args.command == 'checklist'
        assert args.intent == 'checklist'
        assert args.title == 'Tasks'
        assert args.items == 'Votar'
        assert args.print is False

    def test_task_command_with_body(self):
        from printime.cli_parser import create_parser

        parser = create_parser()
        args = parser.parse_args([
            'task', '--title', 'Hoje', '--body', 'comer arroz hoy',
        ])
        assert args.command == 'task'
        assert args.body == 'comer arroz hoy'

    def test_url_command_positional(self):
        from printime.cli_parser import create_parser

        parser = create_parser()
        args = parser.parse_args([
            'url', 'https://example.com/article',
        ])
        assert args.command == 'url'
        assert args.target == 'https://example.com/article'


class TestCmdIntent:
    def test_checklist_preview_by_default(self):
        from printime.intents import cmd_intent

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            intent='checklist',
            template='checklist',
            title='Tasks',
            body=None,
            content=None,
            items='Votar',
            item=None,
            file=None,
            priority=None,
            tags=None,
            caption=None,
            due=None,
            done=False,
            print=False,
            no_cut=False,
            link_qr=False,
            target=None,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            ascii_font='slant',
            ascii_api_fallback=False,
            ascii_strict=False,
            center=False,
        )
        with patch('printime.cli.cmd_print') as mock_print:
            cmd_intent(args, config, printer)
        mock_print.assert_called_once()
        print_args = mock_print.call_args[0][0]
        assert print_args.preview is True
        assert print_args.yes is False

    def test_task_body_reaches_context(self):
        from printime.intents import build_template_context

        args = Namespace(
            intent='task',
            template='task',
            title='Hoje',
            body='comer arroz hoy',
            content=None,
            items=None,
            item=None,
            file=None,
            priority=None,
            tags=None,
            caption=None,
            due=None,
            done=False,
        )
        config = {'printer': {'width': 48}}
        ctx = build_template_context(args, config)
        assert ctx.get('description') == 'comer arroz hoy' or ctx.get('content') == 'comer arroz hoy'
