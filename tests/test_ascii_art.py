#!/usr/bin/env python3
"""Tests for receipt-safe ASCII art rendering."""

import os
import sys
import types
from argparse import Namespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class FakeFiglet:
    """Tiny pyfiglet stand-in with deterministic widths for wrapping tests."""

    def __init__(self, font='slant', width=80):
        self.font = os.path.splitext(os.path.basename(font))[0]
        self.font_arg = font
        self.width = width

    def renderText(self, text):
        scale = {
            'slant': 4,
            'pagga': 3,
            'small': 2,
            'mini': 1,
        }.get(self.font, 4)
        line = ''.join(ch * scale if ch != ' ' else ' ' * scale for ch in text.upper())
        return f'{line}\n{line}\n'


def install_fake_pyfiglet(monkeypatch):
    fake = types.SimpleNamespace(Figlet=FakeFiglet)
    monkeypatch.setitem(sys.modules, 'pyfiglet', fake)


def test_render_ascii_art_wraps_words_by_rendered_width(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('one two three four five', font='slant', width=24)

    assert result.font == 'slant'
    assert len(result.chunks) > 1
    assert result.plain_text == 'one two three four five'
    assert all(len(line) <= 24 for line in result.lines)


def test_render_ascii_art_falls_back_to_compact_font_for_wide_word(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('abcdefghij', font='slant', width=3)

    assert result.font != 'slant'
    assert result.font in {'small', 'mini'}
    assert all(len(line) <= 3 for line in result.lines)
    assert result.warnings


def test_render_ascii_art_splits_long_word_before_font_fallback(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('oristidesxxxzz', font='pagga', width=24)

    assert result.font == 'pagga'
    assert result.chunks == ['oristide', 'sxxxzz']
    assert all(len(line) <= 24 for line in result.lines)


def test_pagga_preserves_figlet_spacing(monkeypatch):
    class BlockPaggaFiglet(FakeFiglet):
        def renderText(self, text):
            if self.font == 'pagga':
                line = '░█▀█░█▀▄'
                return f'{line}\n{line}\n{line}\n'
            return super().renderText(text)

    fake = types.SimpleNamespace(Figlet=BlockPaggaFiglet)
    monkeypatch.setitem(sys.modules, 'pyfiglet', fake)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('ab', font='pagga', width=48)

    assert result.font == 'pagga'
    assert result.lines[0].startswith('░')


def test_api_font_name_maps_public_names():
    from printime.services.ascii_art import _api_font_name

    assert _api_font_name('pagga') == 'Pagga'
    assert _api_font_name('avatar') == 'Avatar'
    assert _api_font_name('slant') == 'Slant'


def test_render_api_uses_capitalized_pagga_name(monkeypatch):
    seen = {}

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(url, timeout=8):
        seen['url'] = url
        return FakeResponse('░█▀█\n░█░█\n░▀▀▀\n')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    from printime.services.ascii_art import _render_api

    lines = _render_api('O', 'pagga')

    assert 'font=Pagga' in seen['url']
    assert lines == ['░█▀█', '░█░█', '░▀▀▀']


def test_pagga_condensing_drops_blank_rows(monkeypatch):
    class TallPaggaFiglet(FakeFiglet):
        def renderText(self, text):
            if self.font == 'pagga':
                return f'{text.upper()}\n\n{text.upper()}\n'
            return super().renderText(text)

    fake = types.SimpleNamespace(Figlet=TallPaggaFiglet)
    monkeypatch.setitem(sys.modules, 'pyfiglet', fake)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('ab', font='pagga', width=6)

    assert result.lines == ['AB', 'AB']


def test_pagga_condensing_drops_blank_rows_between_chunks(monkeypatch):
    class GappyPaggaFiglet(FakeFiglet):
        def renderText(self, text):
            if self.font == 'pagga':
                row = text.upper()
                return f'{row}\n{row}\n{row}\n\n'
            return super().renderText(text)

    fake = types.SimpleNamespace(Figlet=GappyPaggaFiglet)
    monkeypatch.setitem(sys.modules, 'pyfiglet', fake)
    from printime.services.ascii_art import render_ascii_art

    result = render_ascii_art('aaabbb', font='pagga', width=3)

    assert result.font == 'pagga'
    assert len(result.chunks) > 1
    assert all(line.strip() for line in result.lines)
    assert result.lines.count('') == 0


def test_render_ascii_art_rejects_unsupported_public_font(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.ascii_art import AsciiArtError, render_ascii_art

    try:
        render_ascii_art('hello', font='shadow', width=48)
    except AsciiArtError as exc:
        assert 'Supported fonts:' in str(exc)
        assert 'pagga' in str(exc)
    else:
        raise AssertionError('unsupported font should fail')


def test_ascii_fonts_command_lists_limited_options(capsys):
    from printime.cli import cmd_ascii_fonts

    cmd_ascii_fonts()

    output = capsys.readouterr().out
    assert 'Supported ASCII art fonts' in output
    assert 'pagga' in output
    assert 'slant' in output
    assert 'shadow' not in output


def test_pagga_uses_pyfiglet_toilet_font_name(monkeypatch):
    seen = {}

    class CapturingFiglet(FakeFiglet):
        def __init__(self, font='slant', width=80):
            super().__init__(font=font, width=width)
            seen['font'] = font

    fake = types.SimpleNamespace(Figlet=CapturingFiglet)
    monkeypatch.setitem(sys.modules, 'pyfiglet', fake)
    from printime.services.ascii_art import render_ascii_art

    render_ascii_art('oriel', font='pagga', width=48)

    assert seen['font'] == 'pagga'


def test_parse_ascii_fence_options_supports_font_and_alignment():
    from printime.services.markdown_blocks import parse_ascii_fence_options

    opts = parse_ascii_fence_options('font=pagga --center --api-fallback')

    assert opts['font'] == 'pagga'
    assert opts['align'] == 'center'
    assert opts['api_fallback'] is True


def test_ascii_fence_alias_builds_segment(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.markdown_blocks import build_print_segments

    md = """Before

```slant --center
hello world
```

After
"""

    segments = build_print_segments(md, width=48, link_qr=False)
    assert [seg['type'] for seg in segments] == ['styled', 'ascii_art', 'styled']
    ascii_seg = segments[1]
    assert ascii_seg['font'] == 'slant'
    assert ascii_seg['align'] == 'center'
    assert ascii_seg['text'] == 'hello world'
    assert ascii_seg['lines']
    assert all(len(line) <= 48 for line in ascii_seg['lines'])


def test_ascii_fence_joins_multiline_payload(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.markdown_blocks import build_print_segments

    md = """```slant
one two
three four
five
```"""

    segments = build_print_segments(md, width=48, link_qr=False)

    assert segments[0]['text'] == 'one two three four five'
    assert len(segments[0]['chunks']) > 1


def test_markdown_text_with_ascii_fence_uses_segment_preview(monkeypatch, capsys):
    install_fake_pyfiglet(monkeypatch)
    from printime.cli import cmd_print

    printer = MagicMock()
    config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
    args = Namespace(
        test=None,
        image=None,
        mermaid=None,
        text='```slant\nhi\n```',
        ascii=None,
        ascii_font='slant',
        ascii_api_fallback=False,
        ascii_strict=False,
        template=None,
        url=None,
        md=None,
        qr=None,
        bold=False,
        center=False,
        double_height=False,
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
        markdown=True,
        link_qr=False,
        ticket=None,
        input=None,
    )

    cmd_print(args, config, printer)

    output = capsys.readouterr().out
    assert 'HH' in output
    assert 'Preview only. Add --yes to print.' in output
    printer.text.assert_not_called()


def test_template_content_with_ascii_fence_uses_segments(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.services.enrich import enrich_context_fields

    context = {
        'title': 'Banner',
        'content': '```pagga --center\nhello\n```',
    }

    enriched = enrich_context_fields(context, width=48, markdown=True)

    assert enriched['template'] == 'document'
    assert enriched['segments'][0]['type'] == 'ascii_art'
    assert enriched['segments'][0]['font'] == 'pagga'


def test_print_segments_prints_ascii_art_lines(monkeypatch):
    install_fake_pyfiglet(monkeypatch)
    from printime.cli import print_segments

    printer = MagicMock()
    config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
    context = {
        'segments': [{
            'type': 'ascii_art',
            'text': 'hi',
            'font': 'slant',
            'align': 'center',
            'lines': ['  HHII  ', '  HHII  '],
        }],
    }

    print_segments(printer, config, 'document', context, cut=False)

    printer.text.assert_called_once_with('  HHII  \n  HHII  ', align='left')
    assert printer.cut.call_count == 0
