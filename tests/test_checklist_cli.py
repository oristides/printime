"""Tests for checklist --items / --item CLI flags and parsing."""

import os

import pytest

from printime.preview import render_template_preview
from printime.services.checklist import (
    enrich_checklist_context,
    parse_checklist_item,
    parse_checklist_items_string,
)


class TestParseChecklistItem:
    def test_unchecked_plain(self):
        assert parse_checklist_item('Milk') == {'text': 'Milk', 'checked': False}

    def test_checked_double_colon_x(self):
        assert parse_checklist_item('Bread::x') == {'text': 'Bread', 'checked': True}

    def test_checked_double_colon_checked(self):
        assert parse_checklist_item('Bread::checked') == {'text': 'Bread', 'checked': True}

    def test_checked_case_insensitive(self):
        assert parse_checklist_item('Bread::X') == {'text': 'Bread', 'checked': True}
        assert parse_checklist_item('Bread::Checked') == {'text': 'Bread', 'checked': True}

    def test_text_with_single_colon_stays_unchecked(self):
        item = parse_checklist_item('Deploy: staging')
        assert item == {'text': 'Deploy: staging', 'checked': False}

    def test_unrecognized_double_colon_suffix_stays_literal(self):
        item = parse_checklist_item('Note:: review later')
        assert item == {'text': 'Note:: review later', 'checked': False}

    def test_empty_item_raises(self):
        with pytest.raises(ValueError, match='empty'):
            parse_checklist_item('   ')

    def test_checked_without_label_raises(self):
        with pytest.raises(ValueError, match='empty'):
            parse_checklist_item('::x')


class TestParseChecklistItemsString:
    def test_pipe_separated_list(self):
        items = parse_checklist_items_string('Milk|Bread::x|Eggs')
        assert [i['text'] for i in items] == ['Milk', 'Bread', 'Eggs']
        assert items[1]['checked'] is True

    def test_long_market_list(self):
        raw = '|'.join([
            'Milk', 'Bread::x', 'Eggs', 'Butter', 'Cheese', 'Yogurt', 'Rice',
            'Pasta', 'Tomatoes', 'Onions', 'Garlic', 'Olive oil', 'Coffee::x',
        ])
        items = parse_checklist_items_string(raw)
        assert len(items) == 13
        assert items[1]['checked'] is True
        assert items[-1]['checked'] is True

    def test_ignores_empty_segments(self):
        items = parse_checklist_items_string('Milk||Bread::x|')
        assert len(items) == 2

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match='empty'):
            parse_checklist_items_string('   ')


class TestEnrichChecklistContext:
    def test_cli_items_string(self):
        ctx = enrich_checklist_context(
            {'title': 'Market'},
            template='checklist',
            cli_items_string='Milk|Bread::x',
            width=48,
        )
        assert len(ctx['items']) == 2
        assert ctx['items'][1]['checked'] is True

    def test_cli_items_merge_with_file_items(self):
        ctx = enrich_checklist_context(
            {'title': 'Shop', 'items': [{'text': 'Eggs', 'checked': False}]},
            template='checklist',
            cli_items=['Milk', 'Bread::x'],
            width=48,
        )
        assert [i['text'] for i in ctx['items']] == ['Eggs', 'Milk', 'Bread']
        assert ctx['items'][-1]['checked'] is True

    def test_content_checkbox_lines_become_items(self):
        ctx = enrich_checklist_context(
            {'title': 'Tasks', 'content': '- [ ] Milk\n- [x] Bread'},
            template='checklist',
            width=48,
        )
        assert ctx['items'] == [
            {'text': 'Milk', 'checked': False},
            {'text': 'Bread', 'checked': True},
        ]
        assert 'content' not in ctx

    def test_content_prose_kept_without_checkboxes(self):
        ctx = enrich_checklist_context(
            {
                'title': 'Retro',
                'content': 'Sprint went well.',
                'items': [{'text': 'Done', 'checked': True}],
            },
            template='checklist',
            width=48,
        )
        assert 'Sprint went well.' in ctx['content']
        assert len(ctx['items']) == 1


class TestChecklistMarkdownNoDuplicate:
    def test_checkbox_only_markdown_has_no_content(self):
        from printime.services.transform import markdown_to_context

        md = """---
title: Groceries
---

- [ ] Milk
- [x] Bread
"""
        ctx = markdown_to_context(md, 'groceries.md', 48)
        assert ctx['template'] == 'checklist'
        assert len(ctx['items']) == 2
        assert not ctx.get('content')

    def test_checkbox_only_preview_renders_items_once(self):
        from printime.services.transform import markdown_to_context

        md = """---
title: Groceries
---

- [ ] Milk
- [x] Bread
"""
        ctx = markdown_to_context(md, 'groceries.md', 48)
        rendered = render_template_preview('checklist', ctx, width=48)
        assert rendered.count('[ ] Milk') == 1
        assert rendered.count('[X] Bread') == 1


class TestCmdPrintChecklistItems:
    def test_template_checklist_with_items_string(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text=None,
            template='checklist',
            url=None,
            md=None,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=True,
            file=None,
            title='Shopping',
            content=None,
            items='Milk|Bread::x|Eggs',
            item=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            link_qr=False,
        )
        with patch('builtins.print') as mock_print:
            cmd_print(args, config, printer)
            output = '\n'.join(str(c[0][0]) for c in mock_print.call_args_list)
        assert 'SHOPPING' in output
        assert '[ ] Milk' in output
        assert '[X] Bread' in output
        assert '[ ] Eggs' in output
        assert '- [ ]' not in output

    def test_template_checklist_with_item_flags(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text=None,
            template='checklist',
            url=None,
            md=None,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=True,
            file=None,
            title='Shopping',
            content=None,
            item=['Milk', 'Bread::x', 'Eggs'],
            items=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            link_qr=False,
        )
        with patch('builtins.print') as mock_print:
            cmd_print(args, config, printer)
            output = '\n'.join(str(c[0][0]) for c in mock_print.call_args_list)
        assert 'SHOPPING' in output
        assert '[ ] Milk' in output
        assert '[X] Bread' in output
        assert '[ ] Eggs' in output
        assert '- [ ]' not in output

    def test_item_flags_auto_select_checklist_template(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text=None,
            template=None,
            url=None,
            md=None,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=True,
            file=None,
            title='Today',
            content=None,
            item=['Ship docs'],
            items=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            link_qr=False,
        )
        with patch('builtins.print') as mock_print:
            cmd_print(args, config, printer)
            output = '\n'.join(str(c[0][0]) for c in mock_print.call_args_list)
        assert '[ ] Ship docs' in output

    def test_loaded_checklist_md_no_duplicate_items(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        examples = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples')
        md_path = os.path.join(examples, 'checklist.md')
        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text=None,
            template='checklist',
            url=None,
            md=md_path,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=True,
            file=None,
            title=None,
            content=None,
            item=None,
            items=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            link_qr=False,
        )
        with patch('builtins.print') as mock_print:
            cmd_print(args, config, printer)
            output = '\n'.join(str(c[0][0]) for c in mock_print.call_args_list)
        assert output.count('[ ] Milk') == 1
        assert output.count('[X] Bread') == 1

    def test_items_string_auto_select_checklist_template(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text=None,
            template=None,
            url=None,
            md=None,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=True,
            file=None,
            title='Market',
            content=None,
            item=None,
            items='Milk|Bread::x',
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
            link_qr=False,
        )
        with patch('builtins.print') as mock_print:
            cmd_print(args, config, printer)
            output = '\n'.join(str(c[0][0]) for c in mock_print.call_args_list)
        assert '[ ] Milk' in output
        assert '[X] Bread' in output
