#!/usr/bin/env python3
"""Tests for ESC/POS styled markdown lines."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from printime.styled import markdown_to_print_lines


class TestStyledHeadings:
    def test_h1_max_size_not_auto_bold(self):
        lines = markdown_to_print_lines('# Title\n\nBody', 48)
        h1 = next(l for l in lines if l.text == 'Title')
        assert h1.double_height and h1.double_width
        assert not h1.bold
        assert not any(l.text.startswith('=') for l in lines)

    def test_h1_bold_only_with_markdown(self):
        lines = markdown_to_print_lines('# **Title**', 48)
        h1 = next(l for l in lines if l.text == 'Title')
        assert h1.bold

    def test_h2_second_size(self):
        lines = markdown_to_print_lines('## Section', 48)
        h2 = next(l for l in lines if l.text == 'Section')
        assert h2.double_height and not h2.double_width and not h2.bold
        assert not any(l.text.startswith('-') for l in lines)

    def test_h3_third_size(self):
        lines = markdown_to_print_lines('### Sub', 48)
        h3 = next(l for l in lines if l.text == 'Sub')
        assert h3.double_width and not h3.double_height and not h3.bold

    def test_body_after_h3_stays_normal(self):
        md = '### Sub\n\nHello world\n\nPlain line'
        lines = markdown_to_print_lines(md, 48)
        body = [l for l in lines if l.text in ('Hello world', 'Plain line')]
        assert len(body) == 2
        for line in body:
            assert not line.double_width
            assert not line.double_height
            assert line.align == 'left'

    def test_headings_left_aligned_by_default(self):
        lines = markdown_to_print_lines('# One\n## Two\n### Three', 48)
        for text in ('One', 'Two', 'Three'):
            line = next(l for l in lines if l.text == text)
            assert line.align == 'left'

    def test_heading_center_only_with_html(self):
        lines = markdown_to_print_lines('## <center>Centered</center>', 48)
        line = next(l for l in lines if l.text == 'Centered')
        assert line.align == 'center'

    def test_format_print_line_left_aligns_h3(self):
        from printime.styled import PrintLine, format_print_line

        h3 = PrintLine('heading 3', align='left', double_width=True)
        formatted = format_print_line(h3, 48)
        assert formatted.startswith('heading 3')

    def test_inline_headings_on_one_line_split(self):
        lines = markdown_to_print_lines('# One ## Two ### Three', 48)
        texts = [line.text for line in lines if line.text]
        assert texts == ['One', 'Two', 'Three']

    def test_blank_lines_preserved(self):
        lines = markdown_to_print_lines('Line one\n\nLine two', 48)
        assert lines[0].text == 'Line one'
        assert lines[1].text == ''
        assert lines[2].text == 'Line two'

    def test_normalize_splits_jammed_headings(self):
        from printime.styled import normalize_markdown_text

        text = normalize_markdown_text('# Headin1 ## heading 2 ### heading 3')
        assert text.split('\n') == ['# Headin1', '## heading 2', '### heading 3']


    def test_format_print_line_left_aligns_body(self):
        from printime.styled import PrintLine, format_print_line

        body = PrintLine('Hello world', align='left')
        formatted = format_print_line(body, 48)
        assert formatted.startswith('Hello world')

    def test_print_title_block_multiline(self):
        from unittest.mock import MagicMock

        from printime.cli import _print_title_block

        printer = MagicMock()
        printer._write = MagicMock()
        printer._write_style = MagicMock()
        _print_title_block(printer, 'Login Flow', 48, caption='Happy path only')
        payload = b''.join(call.args[0] for call in printer._write.call_args_list)
        text = payload.decode('utf-8')
        assert text.count('\r\n') >= 4
        assert 'LOGIN FLOW' in text
        assert 'Happy path only' in text
        assert '=' * 48 in text

    def test_escpos_text_always_line_feeds(self):
        from unittest.mock import MagicMock

        from printime.cli import EscposPrinterAdapter

        inner = MagicMock()
        printer = EscposPrinterAdapter(inner, width=48)
        printer.text('Hello')
        inner._raw.assert_any_call(b'\r\n')

    def test_print_styled_lines_feeds_after_double_height(self):
        from unittest.mock import MagicMock

        from printime.cli import print_styled_lines
        from printime.styled import PrintLine

        printer = MagicMock()
        printer._write = MagicMock()
        lines = [
            PrintLine('Title', double_height=True, double_width=True),
            PrintLine(''),
            PrintLine('Body'),
        ]
        print_styled_lines(printer, lines)
        assert printer.text.call_count == 2
        assert any(call.args[0] == b'\r\n' for call in printer._write.call_args_list)

    def test_markdown_table_renders_as_receipt_table(self):
        lines = markdown_to_print_lines(
            '| Header 1 | Header 2 |\n'
            '| -------- | -------- |\n'
            '| Cell A   | Cell B   |\n'
            '| Cell C   | Cell D   |',
            48,
        )
        texts = [line.text for line in lines if line.text]

        assert any('Header 1' in text and 'Header 2' in text for text in texts)
        assert any('Cell A' in text and 'Cell B' in text for text in texts)
        assert not any(text.startswith('|') for text in texts)
        assert not any('-------- | --------' in text for text in texts)

    def test_anytype_table_with_br_markup_renders_cleanly(self):
        table = (
            '|| de   <br> | dsd   <br> | 123   <br> | das     |\n'
            '|<br> |                                          |\n'
            '||:----------|:-----------|:-----------|:--------|\n'
            '|---|                                            |\n'
            '|| ss   <br> |       <br> |   a   <br> | das     |\n'
            '|<br> |                                          |\n'
            '|| wd   <br> |  sa   <br> | 312   <br> | 123     |'
        )

        lines = markdown_to_print_lines(table, 48)
        texts = [line.text for line in lines if line.text]

        assert any('de' in text and 'dsd' in text for text in texts)
        assert any(
            'ss' in text and 'a' in text and 'das' in text
            for text in texts
        )
        assert any(
            'wd' in text and 'sa' in text and '312' in text
            for text in texts
        )
        assert not any('<br>' in text for text in texts)
        assert not any(text.startswith('|') for text in texts)

    def test_four_column_table_fits_receipt_width(self):
        lines = markdown_to_print_lines(
            '| Metric | Owner | Status | Next |\n'
            '| --- | --- | --- | --- |\n'
            '| Activation | Ana | Green | Watch signups |\n'
            '| Churn | Bob | Yellow | Call accounts |\n'
            '| Cash | Lia | Red | Cut spend |',
            48,
        )
        texts = [line.text for line in lines if line.text]

        assert any('Metric' in text and 'Owner' in text for text in texts)
        assert any('Activation' in text and 'Green' in text for text in texts)
        assert any('Call' in text and 'accounts' in text for text in texts)
        assert all(len(text) <= 48 for text in texts)

    def test_five_column_table_wraps_cells_to_receipt_width(self):
        lines = markdown_to_print_lines(
            '| Area | DRI | Risk | Due | Note |\n'
            '| --- | --- | --- | --- | --- |\n'
            '| API | Ana | Low | Mon | Ship |\n'
            '| Billing | Bob | Medium | Tue | Needs review |\n'
            '| Support | Lia | High | Fri | Escalate customer issue |',
            48,
        )
        texts = [line.text for line in lines if line.text]

        assert any('Area' in text and 'Risk' in text for text in texts)
        assert any('Billing' in text and 'Medium' in text for text in texts)
        assert any('Escalate' in text for text in texts)
        assert all(len(text) <= 48 for text in texts)

    def test_table_cells_strip_enriched_markdown(self):
        lines = markdown_to_print_lines(
            '| **Priority** | ### Owner | Result |\n'
            '| --- | --- | --- |\n'
            '| **P0** | ## Ana | `Done` |\n'
            '| P1 | Bob | [Spec](https://example.com) |',
            48,
        )
        texts = [line.text for line in lines if line.text]

        assert any('Priority' in text and 'Owner' in text for text in texts)
        assert any('P0' in text and 'Ana' in text and 'Done' in text for text in texts)
        assert any('Spec' in text for text in texts)
        assert not any('**' in text or '###' in text or '`' in text for text in texts)

    def test_enriched_markdown_around_table_keeps_headings_and_bold(self):
        lines = markdown_to_print_lines(
            '# Weekly Review\n\n'
            '**Top risks**\n\n'
            '| Risk | Owner | Status | Action |\n'
            '| --- | --- | --- | --- |\n'
            '| Scope | Ana | Yellow | Reduce |\n'
            '| Launch | Bob | Green | Continue |\n\n'
            '## Follow up',
            48,
        )

        assert any(line.text == 'Weekly Review' for line in lines)
        assert any(line.text == 'Top risks' and line.bold for line in lines)
        assert any('Scope' in line.text and 'Yellow' in line.text for line in lines)
        assert any(line.text == 'Follow up' for line in lines)
