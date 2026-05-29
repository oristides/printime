#!/usr/bin/env python3
"""Test suite for printime."""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from printime.cli import RawPrinter, load_config, load_context_file, render_for_print, render_template
from printime.preview import (
    PaperPreview,
    center_text,
    ljust_text,
    rjust_text,
    render_template_for_print,
    render_template_preview,
    sanitize_printer_text,
)
from printime.services.transform import markdown_to_context


class TestPaperPreview:
    def test_initialization(self):
        preview = PaperPreview()
        assert len(preview.lines) >= 1
        assert '=' in preview.lines[0]

    def test_add_line(self):
        preview = PaperPreview()
        preview._add_line("Hello World")
        assert any('Hello World' in line for line in preview.lines)

    def test_footer_adds_cut_guide(self):
        preview = PaperPreview()
        preview.footer()
        assert "[CUT]" in str(preview.lines)


class TestTextHelpers:
    def test_center_text(self):
        result = center_text("Hi", 10)
        assert len(result) == 10
        assert result == "    Hi    "

    def test_ljust_text(self):
        result = ljust_text("Hi", 10)
        assert len(result) == 10
        assert result == "Hi        "

    def test_rjust_text(self):
        result = rjust_text("Hi", 10)
        assert len(result) == 10
        assert result == "        Hi"


class TestRawPrinter:
    def test_initialization(self):
        config = load_config()
        printer = RawPrinter(config)
        assert printer.width == config['printer']['width']

    def test_text_adds_crlf(self):
        config = load_config()
        printer = RawPrinter(config)
        printer._buffer = b''
        printer.text("Test")
        assert b'\r\n' in printer._buffer


class TestTemplates:
    def test_load_note_template(self):
        config = load_config()
        result = render_template('note', {
            'title': 'Test Note',
            'content': 'Test content',
        }, config)
        assert result is not None
        assert 'TEST NOTE' in result
        assert 'Test content' in result

    def test_key_templates_include_minute_precision_datetime(self):
        from printime.preview import render_template_for_print

        config = load_config()
        contexts = {
            'note': {'title': 'Note', 'content': 'Body'},
            'checklist': {
                'title': 'List',
                'items': [{'text': 'Milk', 'checked': False}],
            },
            'message': {'title': 'Message', 'content': 'Hello'},
            'agenda': {
                'title': 'Today',
                'days': [{'label': 'Today', 'events': []}],
                'empty_message': 'No events scheduled.',
                'source': 'Google Calendar',
            },
            'email': {
                'subject': 'Subject',
                'sender': 'a@b.com',
                'to': 'c@d.com',
                'body': 'Body',
            },
            'document': {'title': 'Doc', 'content': 'Body'},
            'jira': {
                'ticket_id': 'ABC-1',
                'summary': 'Fix bug',
                'description': 'Details',
            },
            'task': {'title': 'Task', 'description': 'Do thing'},
            'ticket': {'title': 'Event', 'caption': 'Venue'},
            'heading': {'text': 'Section', 'style': 'bar'},
            'receipt': {
                'store_name': 'Shop',
                'items': [{'name': 'Item', 'price': '1.00'}],
                'total': '1.00',
            },
        }

        for template_name, context in contexts.items():
            rendered = render_template_for_print(template_name, context, config)
            assert re.search(
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}',
                rendered,
            ), template_name
            assert not re.search(
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                rendered,
            ), template_name

    def test_diagram_and_equation_skip_print_timestamp(self):
        from printime.preview import render_template_for_print

        config = load_config()
        ts = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}'
        for template_name, context in {
            'diagram': {'title': 'Flow', 'mermaid': 'graph TD; A-->B'},
            'equation': {'latex': 'E=mc^2'},
        }.items():
            rendered = render_template_for_print(template_name, context, config)
            assert not re.search(ts, rendered), template_name

    def test_load_email_template(self):
        config = load_config()
        result = render_template('email', {
            'subject': 'Deploy tonight',
            'sender': 'ana@company.com',
            'to': 'oriel@company.com',
            'body': 'Please review before 6pm.',
        }, config)
        assert 'EMAIL' in result
        assert 'Deploy tonight' in result
        assert 'ana@company.com' in result
        assert 'Please review before 6pm.' in result

    def test_load_checklist_template(self):
        config = load_config()
        result = render_template('checklist', {
            'title': 'Shopping',
            'items': [
                {'text': 'Milk', 'checked': False},
                {'text': 'Bread', 'checked': True},
            ],
        }, config)
        assert result is not None
        assert 'SHOPPING' in result
        assert '[ ]' in result
        assert '[X]' in result


class TestPreviewRendering:
    def test_render_note_preview(self):
        result = render_template_preview('note', {
            'title': 'Meeting Notes',
            'content': 'Discuss items',
            'priority': 'HIGH',
            'tags': ['work'],
        })
        assert '|' in result
        assert 'MEETING NOTES' in result
        assert '[CUT]' in result

    def test_render_checklist_preview(self):
        result = render_template_preview('checklist', {
            'title': 'Todo',
            'items': [
                {'text': 'Item 1', 'checked': True},
                {'text': 'Item 2', 'checked': False},
            ],
        })
        assert '|' in result
        assert 'TODO' in result
        assert '[X]' in result
        assert '[ ]' in result
        assert '[CUT]' in result

    def test_render_task_preview_with_content(self):
        from printime.cli import _finalize_template_context
        from argparse import Namespace

        config = {'printer': {'width': 48}}
        args = Namespace(template='task', item=None, items=None, link_qr=False)
        context = _finalize_template_context(
            {'title': 'Tarefas de Hoje', 'content': 'Votar hoy'},
            args,
            config,
        )
        result = render_template_preview('task', context)
        assert 'TAREFAS DE HOJE' in result
        assert 'Votar hoy' in result

    def test_print_template_preview_only_does_not_print(self, monkeypatch):
        from unittest.mock import MagicMock
        import printime.cli as cli

        printed = []
        monkeypatch.setattr(cli, 'print_rendered', lambda *args, **kwargs: printed.append(args))

        cli._print_template(
            MagicMock(),
            {'printer': {'width': 48}},
            'note',
            {'title': 'Preview', 'content': 'Only'},
            preview=True,
            yes=False,
        )

        assert not printed

    def test_print_template_preview_yes_prints_after_preview(self, monkeypatch):
        from unittest.mock import MagicMock
        import printime.cli as cli

        printed = []
        monkeypatch.setattr(cli, 'print_rendered', lambda *args, **kwargs: printed.append(args))

        cli._print_template(
            MagicMock(),
            {'printer': {'width': 48}},
            'note',
            {'title': 'Preview', 'content': 'Then print'},
            preview=True,
            yes=True,
        )

        assert printed


class TestMarkdownContext:
    def test_load_markdown_context(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'oriel-mandates.md')
        context = load_context_file(path)
        assert context['title'] == 'Oriel mandates'
        assert 'Self-guided' in context['content']

    def test_checklist_from_markdown(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'checklist.md')
        context = load_context_file(path)
        assert context['template'] == 'checklist'
        assert context['title'] == 'Weekly Shopping List'
        assert len(context['items']) == 5
        assert context['items'][1]['checked'] is True

    def test_checkbox_parsing(self):
        md = """---
title: Groceries
---

- [ ] Milk
- [x] Bread
"""
        context = markdown_to_context(md, 'groceries.md', 48)
        assert context['template'] == 'checklist'
        assert context['items'][0]['checked'] is False
        assert context['items'][1]['checked'] is True

    def test_checklist_includes_body_text(self):
        md = """# RETROSUM

Sprint went well overall.
Watch scope creep next time.

- [x] eXEMPLO 2
- [ ] DEDED
"""
        context = markdown_to_context(md, 'retro.md', 48)
        assert context['template'] == 'checklist'
        assert 'Sprint went well' in context.get('content', '')
        assert len(context['items']) == 2

    def test_checklist_template_renders_content(self):
        rendered = render_template_preview(
            'checklist',
            {
                'title': 'RETROSUM',
                'content': 'Sprint went well overall.',
                'items': [{'text': 'Done item', 'checked': True}],
            },
            width=48,
        )
        assert 'Sprint went well' in rendered
        assert 'Done item' in rendered

    def test_heading_levels_in_content(self):
        md = """---
title: Page
---
## Section
### Sub
Body line
"""
        ctx = markdown_to_context(md, 'x.md', 48)
        lines = ctx['content_lines']
        h2 = next(l for l in lines if l.text == 'Section')
        h3 = next(l for l in lines if l.text == 'Sub')
        assert h2.double_height and not h2.bold
        assert h3.double_width and not h3.bold
        assert 'Section' in ctx['content']
        assert 'Sub' in ctx['content']

    def test_document_preview_title_between_rules(self):
        from printime.cli import load_context_file
        from printime.preview import render_template_preview
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'examples', 'diagram_flow.md',
        )
        ctx = load_context_file(path)
        lines = render_template_preview('document', ctx).split('\n')
        title_idx = next(i for i, line in enumerate(lines) if 'LOGIN FLOW' in line)
        assert lines[title_idx - 1].strip('|').strip() == '=' * 48
        assert 'Happy path only' in lines[title_idx + 1]
        assert lines[title_idx + 2].strip('|').strip() == '=' * 48

    def test_document_caption_in_title_block(self):
        from printime.cli import load_context_file
        from printime.preview import render_template_preview
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'examples', 'diagram_flow.md',
        )
        ctx = load_context_file(path)
        rendered = render_template_preview('document', ctx)
        title = rendered.index('LOGIN FLOW')
        caption = rendered.index('Happy path only')
        diagram = rendered.index('[diagram]')
        assert title < caption < diagram
        lines = rendered.split('\n')
        cap_idx = next(i for i, line in enumerate(lines) if 'Happy path only' in line)
        assert 'LOGIN FLOW' in lines[cap_idx - 1]
        assert lines[cap_idx + 1].strip('|').strip() == '=' * 48

    def test_document_preview_checklist_one_item_per_line(self):
        from printime.cli import load_context_file
        from printime.preview import render_template_preview
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'examples', 'diagram_flow.md',
        )
        ctx = load_context_file(path)
        rendered = render_template_preview('document', ctx)
        milk = rendered.index('[ ] Milkssdsd')
        bread = rendered.index('[X] Bread')
        eggs = rendered.index('[ ] Eggs')
        assert milk < bread < eggs
        assert rendered[milk:bread].count('\n') >= 1
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'examples', 'diagram_flow.md',
        )
        ctx = load_context_file(path)
        assert ctx['template'] == 'document'
        assert ctx.get('mermaid')
        assert len(ctx['items']) == 4
        assert 'HEADIN1' in ctx['content'] or any(
            l.text == 'Headin1' for l in ctx.get('content_lines', [])
        )
        rendered = render_template_preview('document', ctx, width=48)
        assert '[diagram]' in rendered
        assert 'Happy path only' in rendered
        assert 'Bread' in rendered


class TestPreviewPrintMatch:
    def test_print_output_has_no_cut_guide(self):
        config = load_config()
        ctx = load_context_file(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'checklist.md')
        )
        output = render_for_print('checklist', ctx, config)
        assert '[CUT]' not in output
        assert 'WEEKLY SHOPPING LIST' in output
        assert '[X]' in output

    def test_print_output_has_no_preview_borders(self):
        config = load_config()
        ctx = {'title': 'Test', 'content': 'Hello'}
        output = render_template_for_print('note', ctx, config)
        assert not output.startswith('|')
        assert '[CUT]' not in output

    def test_sanitize_printer_text(self):
        assert sanitize_printer_text('• item') == '* item'


class TestTextPreview:
    def test_render_text_preview_centered_bold(self):
        from printime.preview import render_text_preview

        rendered = render_text_preview('URGENT', width=48, bold=True, align='center')
        assert 'URGENT' in rendered
        assert '[CUT]' in rendered
        assert rendered.startswith('|')


class TestCmdPrint:
    def test_text_prints_once(self):
        from argparse import Namespace
        from unittest.mock import MagicMock

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text='URGENT',
            template=None,
            url=None,
            md=None,
            qr=None,
            bold=True,
            center=True,
            no_cut=False,
            preview=False,
            file=None,
            title=None,
            content=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
        )
        cmd_print(args, config, printer)
        printer.text.assert_called_once_with('URGENT', bold=True, align='center')

    def test_markdown_does_not_also_run_template_block(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        examples = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples')
        md_path = os.path.join(examples, 'checklist.md')
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
            preview=False,
            file=None,
            title=None,
            content=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
        )
        with patch('printime.cli.print_rendered') as mock_print_rendered:
            cmd_print(args, config, printer)
            assert mock_print_rendered.call_count == 1


    def test_text_preview_cancels_without_print(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48}}
        args = Namespace(
            test=None,
            text='URGENT',
            template=None,
            url=None,
            md=None,
            qr=None,
            bold=True,
            center=True,
            no_cut=False,
            preview=True,
            file=None,
            title=None,
            content=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
        )
        with patch('printime.preview.confirm', return_value=False):
            cmd_print(args, config, printer)
        printer.text.assert_not_called()


class TestTemplateList:
    def test_list_one_template_shows_fields(self, capsys):
        from argparse import Namespace

        from printime.cli import cmd_list

        rc = cmd_list(Namespace(template='note', verbose=False))
        out = capsys.readouterr().out
        assert rc == 0
        assert 'title' in out
        assert 'content' in out

    def test_list_unknown_template(self, capsys):
        from argparse import Namespace

        from printime.cli import cmd_list

        rc = cmd_list(Namespace(template='nope', verbose=False))
        assert rc == 1
        assert 'Unknown template' in capsys.readouterr().err


class TestResolveInputPath:
    def test_resolves_examples_from_install_root(self, tmp_path, monkeypatch):
        from printime.cli import resolve_input_path

        monkeypatch.chdir(tmp_path)
        resolved = resolve_input_path('examples/diagram_flow.md')
        assert resolved.endswith('examples/diagram_flow.md')
        assert os.path.isfile(resolved)


class TestCLIHelp:
    def test_main_help(self):
        from printime.cli import main
        with pytest.raises(SystemExit):
            sys.argv = ['printime', '--help']
            main()

    def test_print_help(self):
        from printime.cli import main
        with pytest.raises(SystemExit):
            sys.argv = ['printime', 'print', '--help']
            main()

    def test_invalid_command_suggests_print(self, capsys):
        from printime.cli import main
        with pytest.raises(SystemExit) as exc:
            sys.argv = ['printime', 'prnt']
            main()
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "Did you mean 'print'?" in err

    def test_unknown_flag_suggests_title(self, capsys):
        from printime.cli import main
        with pytest.raises(SystemExit) as exc:
            sys.argv = ['printime', 'print', '--titel', 'foo']
            main()
        assert exc.value.code == 2
        captured = capsys.readouterr()
        assert 'Did you mean --title?' in captured.err
        assert 'printime print' in captured.out

    def test_anytype_without_subcommand_shows_examples(self, capsys):
        from printime.cli import main
        sys.argv = ['printime', 'anytype']
        assert main() == 2
        err = capsys.readouterr().err
        assert 'anytype print' in err

    def test_main_help_lists_intents(self, capsys):
        from printime.cli import main
        with pytest.raises(SystemExit):
            sys.argv = ['printime', '--help']
            main()
        out = capsys.readouterr().out
        assert 'checklist' in out
        assert 'printime checklist' in out or 'checklist' in out
        assert 'task' in out
        assert '--print' in out


class TestIntentHelpEpilogs:
    def test_main_help_disambiguates_task_vs_checklist(self, capsys):
        from printime.cli import main

        with pytest.raises(SystemExit):
            sys.argv = ['printime', '--help']
            main()
        out = capsys.readouterr().out
        assert 'one thing to do' in out
        assert 'list / todos' in out
        assert 'web article' in out
        assert 'scannable QR' in out

    def test_checklist_help_shows_shape_and_body(self, capsys):
        from printime.cli import main

        with pytest.raises(SystemExit):
            sys.argv = ['printime', 'checklist', '--help']
            main()
        out = capsys.readouterr().out
        assert 'printime checklist --items' in out
        assert '--body' in out
        assert 'intro text above the list' in out
        assert 'use task --body instead' in out

    def test_task_help_points_to_checklist_for_lists(self, capsys):
        from printime.cli import main

        with pytest.raises(SystemExit):
            sys.argv = ['printime', 'task', '--help']
            main()
        out = capsys.readouterr().out
        assert 'printime task --body' in out
        assert 'checklist --items' in out

    def test_url_qr_help_disambiguates(self, capsys):
        from printime.cli import main
        import sys

        with pytest.raises(SystemExit):
            sys.argv = ['printime', 'url', '--help']
            main()
        url_out = capsys.readouterr().out
        assert 'Not a QR code' in url_out

        with pytest.raises(SystemExit):
            sys.argv = ['printime', 'qr', '--help']
            main()
        qr_out = capsys.readouterr().out
        assert 'Not a full article' in qr_out


class TestUrlFetch:
    SAMPLE_HTML = """
    <html><head>
    <meta property="og:title" content="Apocalypse No" />
    </head><body>
    <div class="available-content"><div class="body markup">
    <p>First paragraph about the article.</p>
    <h2>Section Two</h2>
    <p>Second paragraph with <strong>bold</strong> text.</p>
    </div></div>
    </body></html>
    """

    def test_html_to_text(self):
        from printime.services.fetch_url import html_to_text, _extract_article_html

        text = html_to_text(_extract_article_html(self.SAMPLE_HTML))
        assert 'First paragraph about the article.' in text
        assert 'Section Two' in text
        assert 'bold' in text

    def test_url_to_context_offline(self):
        from printime.services import fetch_url

        original = fetch_url.fetch_html
        fetch_url.fetch_html = lambda url: self.SAMPLE_HTML
        try:
            context = fetch_url.url_to_context('https://example.com/p/test', width=48, max_chars=None, link_qr=False)
        finally:
            fetch_url.fetch_html = original

        assert context['title'] == 'Apocalypse No'
        assert 'First paragraph' in context['content']
        assert context['template'] == 'note'

    FOLHA_HTML = """
    <html><head>
    <meta property="og:title" content="Crise do Master, diz Gilmar Mendes" />
    </head><body>
    <div itemprop="articleBody">
    <p>O ministro Gilmar Mendes afirma que o escândalo do Banco Master foi endereçado indevidamente.</p>
    <p>Isso certamente está sendo investigado, diz o ministro.</p>
    </div>
    <div class="c-news__footer">footer</div>
    </body></html>
    """

    def test_folha_article_body(self):
        from printime.services.fetch_url import html_to_text, _extract_article_html

        text = html_to_text(_extract_article_html(self.FOLHA_HTML))
        assert 'Gilmar Mendes' in text
        assert 'benefício do assinante' not in text

    def test_twitter_embedded_json(self):
        from printime.services.fetch_url import _extract_twitter

        html = '{"full_text":"How to Get Rich (without getting lucky):","screen_name":"naval"}'
        title, body = _extract_twitter(html)
        assert title == '@naval'
        assert 'How to Get Rich' in body


class TestGoogleCalendar:
    SAMPLE_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/Sao_Paulo:20260523T090000
DTEND;TZID=America/Sao_Paulo:20260523T093000
SUMMARY:Team standup
LOCATION:Google Meet
DESCRIPTION:Discuss blockers\\nand launch notes
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260523
DTEND;VALUE=DATE:20260524
SUMMARY:Birthday
END:VEVENT
END:VCALENDAR
"""

    def test_parse_ics_events(self):
        from datetime import date
        from printime.services.gcal import events_for_day, parse_ics_events
        from zoneinfo import ZoneInfo

        tz = ZoneInfo('America/Sao_Paulo')
        events = parse_ics_events(self.SAMPLE_ICS, tz)
        assert len(events) == 2
        standup = next(
            event for event in events if event.summary == 'Team standup'
        )
        assert standup.description == 'Discuss blockers\nand launch notes'
        today = date(2026, 5, 23)
        day_events = events_for_day(events, today)
        assert len(day_events) == 2
        titles = {event.summary for event in day_events}
        assert titles == {'Team standup', 'Birthday'}

    def test_agenda_context_includes_event_notes(self, monkeypatch):
        from datetime import date
        from printime.services import gcal

        monkeypatch.setattr(gcal, 'fetch_ics', lambda _url: self.SAMPLE_ICS)

        context = gcal.agenda_to_context(
            'https://calendar.example/private.ics',
            timezone='America/Sao_Paulo',
            start_day=date(2026, 5, 23),
        )

        event = context['days'][0]['events'][0]
        assert event['location'] == 'Google Meet'
        assert event['notes'] == 'Discuss blockers\nand launch notes'

    def test_agenda_template_preview(self):
        from printime.preview import render_template_preview

        rendered = render_template_preview('agenda', {
            'title': 'Today — Saturday, May 23',
            'days': [{
                'label': 'Today — Saturday, May 23',
                'events': [
                    {
                        'time': '09:00',
                        'title': 'Team standup',
                        'location': 'Google Meet',
                        'notes': 'Discuss blockers',
                        'all_day': False,
                    },
                ],
            }],
            'empty_message': 'No events scheduled.',
            'source': 'Google Calendar',
        })
        assert 'Team standup' in rendered
        assert '09:00' in rendered
        assert 'Google Meet' in rendered
        assert 'Discuss blockers' in rendered

    def test_agenda_today_flag_prints_single_day(self, monkeypatch):
        import printime.cli as cli

        captured = {}

        def fake_print_agenda(**kwargs):
            captured.update(kwargs)
            return True

        monkeypatch.setattr(
            sys,
            'argv',
            ['printime', 'agenda', '--today', '--preview'],
        )
        monkeypatch.setattr(
            'printime.services.gcal.print_agenda',
            fake_print_agenda,
        )
        monkeypatch.setattr(cli, 'load_config', lambda: {'printer': {'width': 48}})

        assert cli.main() is None
        assert captured['preview'] is True
        assert captured['days'] == 1
        assert captured['start_day'] is None
