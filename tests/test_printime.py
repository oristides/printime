#!/usr/bin/env python3
"""Test suite for printime."""

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
            context = fetch_url.url_to_context('https://example.com/p/test', width=48, max_chars=None)
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
        today = date(2026, 5, 23)
        day_events = events_for_day(events, today)
        assert len(day_events) == 2
        titles = {event.summary for event in day_events}
        assert titles == {'Team standup', 'Birthday'}

    def test_agenda_template_preview(self):
        from printime.preview import render_template_preview

        rendered = render_template_preview('agenda', {
            'title': 'Today — Saturday, May 23',
            'days': [{
                'label': 'Today — Saturday, May 23',
                'events': [
                    {'time': '09:00', 'title': 'Team standup', 'location': 'Google Meet', 'all_day': False},
                ],
            }],
            'empty_message': 'No events scheduled.',
            'source': 'Google Calendar',
        })
        assert 'Team standup' in rendered
        assert '09:00' in rendered
        assert 'Google Meet' in rendered
