#!/usr/bin/env python3
"""Tests for image, mermaid, and diagram printing."""

import os
import sys
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestQrMarkdown:
    def test_parse_qr_payload_strips_quotes(self):
        from printime.services.markdown_blocks import parse_qr_payload

        assert parse_qr_payload('"https://example.com"') == 'https://example.com'

    def test_parse_qr_fence_options(self):
        from printime.services.markdown_blocks import parse_qr_fence_options

        opts = parse_qr_fence_options('--qr-size 10 --show-link')
        assert opts['qr_size'] == 10
        assert opts['show_link'] is True

    def test_extract_qr_block(self):
        from printime.services.markdown_blocks import split_markdown_body

        body = """Hello

```qr --qr-size 10
"https://www.youtube.com/watch?v=7B0IuevRuUU"
```
"""
        parts = split_markdown_body(body)
        assert parts[0][0] == 'markdown'
        assert parts[1][0] == 'qr'
        assert parts[1][2] == '--qr-size 10'
        assert 'youtube.com' in parts[1][1]

    def test_qr_segment_carries_fence_options(self):
        from printime.services.transform import markdown_to_context

        md = """```qr --qr-size 10 --show-link
https://example.com
```"""
        ctx = markdown_to_context(md, 'qr.md', 48)
        qr = next(seg for seg in ctx['segments'] if seg['type'] == 'qr')
        assert qr['qr_size'] == 10
        assert qr['show_link'] is True

    def test_qr_segment_order_after_mermaid(self):
        from printime.services.transform import markdown_to_context

        md = """---
title: Page
---
Text

```mermaid
graph TD
  A --> B
```

```qr
https://example.com
```
"""
        ctx = markdown_to_context(md, 'page.md', 48)
        types = [seg['type'] for seg in ctx['segments']]
        assert types == ['styled', 'mermaid', 'qr']
        assert ctx['segments'][-1]['data'] == 'https://example.com'
        assert ctx['template'] == 'document'

    def test_untagged_fence_detected_as_mermaid(self):
        from printime.services.markdown_blocks import build_print_segments

        body = """Hello

```
graph TD
  A --> B
```
"""
        segments = build_print_segments(body, 48)
        assert [seg['type'] for seg in segments] == ['styled', 'mermaid']
        assert 'graph TD' in segments[1]['source']

    def test_normalize_mermaid_source_fixes_anytype_jam(self):
        from printime.services.markdown_blocks import normalize_mermaid_source

        raw = "graph TD\nB -->|no| D[Login]D —> C"
        fixed = normalize_mermaid_source(raw)
        assert 'D[Login]\nD --> C' in fixed

    def test_anytype_style_markdown_parses_mermaid_and_qr(self):
        from printime.services.anytype import page_to_template_context

        raw = """# Headin1
## heading 2
- [ ] Eggs
```
graph TD
A --> B
```
\\`\\`\\`qr --qr-size 13 --center
"https://example.com"
\\`\\`\\`
"""
        page = {'name': 'Login Flow', 'markdown': raw}
        ctx = page_to_template_context(page, 48)
        types = [seg['type'] for seg in ctx['segments']]
        assert ctx['title'] == 'Login Flow'
        assert ctx['template'] == 'document'
        assert 'mermaid' in types
        assert 'qr' in types

    def test_print_segments_calls_qr(self):
        from printime.cli import print_segments

        printer = MagicMock()
        config = {'printer': {'width': 48, 'paper_width_pixels': 576, 'qr_size': 8}}
        context = {
            'title': 'Test',
            'segments': [{
                'type': 'qr',
                'data': 'https://example.com',
                'qr_size': 10,
                'show_link': True,
            }],
        }
        print_segments(printer, config, 'document', context, cut=False)
        printer.qr.assert_called_once_with('https://example.com', size=10, center=False)
        assert printer.text.call_count >= 2


class TestMermaidExtraction:
    def test_extract_mermaid_block(self):
        from printime.services.diagram import extract_mermaid_from_markdown

        body = """# Flow

```mermaid
graph TD
  A --> B
```

Some notes after.
"""
        blocks, remaining = extract_mermaid_from_markdown(body)
        assert len(blocks) == 1
        assert 'graph TD' in blocks[0]
        assert '```mermaid' not in remaining
        assert 'Some notes after.' in remaining

    def test_extract_mermaid_none(self):
        from printime.services.diagram import extract_mermaid_from_markdown

        blocks, remaining = extract_mermaid_from_markdown('# Just text\n\nHello.')
        assert blocks == []
        assert remaining == '# Just text\n\nHello.'


class TestMarkdownMermaidContext:
    def test_markdown_with_mermaid_sets_diagram_template(self):
        from printime.services.transform import markdown_to_context

        md = """---
title: My Flow
---

```mermaid
graph LR
  Start --> End
```
"""
        ctx = markdown_to_context(md, 'flow.md', 48)
        assert ctx['template'] == 'diagram'
        assert 'graph LR' in ctx['mermaid']
        assert ctx['title'] == 'My Flow'

    def test_markdown_respects_explicit_template(self):
        from printime.services.transform import markdown_to_context

        md = """---
template: note
title: Notes
---

```mermaid
graph TD
  A --> B
```

Extra text.
"""
        ctx = markdown_to_context(md, 'note.md', 48)
        assert ctx['template'] == 'note'
        assert 'mermaid' in ctx
        assert 'Extra text.' in ctx.get('content', '')


class TestMermaidToPng:
    def test_mermaid_to_png_invokes_mmdc(self, tmp_path):
        from PIL import Image

        from printime.services.diagram import mermaid_to_png

        with patch('printime.services.diagram.check_mermaid_cli', return_value=True), patch(
            'printime.services.diagram.subprocess.run',
        ) as mock_run:
            def fake_run(cmd, **kwargs):
                for i, arg in enumerate(cmd):
                    if arg == '-o' and i + 1 < len(cmd):
                        out = cmd[i + 1]
                        Image.new('RGB', (200, 100), 'white').save(out, 'PNG')
                return MagicMock(returncode=0)

            mock_run.side_effect = fake_run
            result = mermaid_to_png(
                'graph TD\n  A --> B',
                output_dir=str(tmp_path),
                width=576,
            )

        assert result is not None
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert '-p' in cmd
        assert '-c' in cmd
        assert '-C' in cmd
        assert 'mmdc' in cmd[0] or cmd[0] == 'npx'


class TestPrepareDiagram:
    def test_prepare_diagram_upscales_small_canvas(self, tmp_path):
        from PIL import Image

        from printime.services.diagram import prepare_diagram_for_print

        src = tmp_path / 'small.png'
        # Small diagram centered in large white canvas (typical mermaid export).
        canvas = Image.new('RGB', (400, 300), 'white')
        box = Image.new('RGB', (120, 80), 'black')
        canvas.paste(box, (140, 110))
        canvas.save(src)

        out = prepare_diagram_for_print(str(src), max_width=576)
        try:
            with Image.open(out) as img:
                assert img.mode == '1'
                assert 120 < img.width < 280
        finally:
            if out != str(src):
                os.unlink(out)

    def test_mermaid_to_png_without_cli_returns_none(self):
        from printime.services.diagram import mermaid_to_png

        with patch('printime.services.diagram.check_mermaid_cli', return_value=False):
            assert mermaid_to_png('graph TD\n  A --> B') is None


class TestPrepareImage:
    def test_prepare_image_scales_wide_image(self, tmp_path):
        from PIL import Image

        from printime.services.diagram import prepare_image_for_print

        src = tmp_path / 'wide.png'
        Image.new('RGB', (800, 400), 'white').save(src)
        out = prepare_image_for_print(str(src), max_width=576)
        try:
            with Image.open(out) as img:
                assert img.width <= 576
        finally:
            if out != str(src):
                os.unlink(out)


class TestPrintImagePage:
    def test_print_image_page_prints_once(self):
        from printime.cli import print_image_page

        printer = MagicMock()
        config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
        with patch('printime.services.diagram.prepare_image_for_print', return_value='/tmp/x.png'):
            print_image_page(
                printer, config, '/tmp/x.png',
                title='Chart', caption='Q1 sales',
            )
        assert printer.image.call_count == 1
        printer.text.assert_any_call('Chart', align='center', bold=True)


class TestCmdPrintImage:
    def test_cmd_print_image(self):
        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
        args = Namespace(
            test=None,
            image='/tmp/chart.png',
            mermaid=None,
            text=None,
            template=None,
            url=None,
            md=None,
            qr=None,
            bold=False,
            center=False,
            no_cut=False,
            preview=False,
            file=None,
            title='Sales',
            content=None,
            priority=None,
            tags=None,
            yes=False,
            qr_size=8,
            show_link=False,
            max_chars=12000,
        )
        with patch('printime.cli.os.path.isfile', return_value=True), patch(
            'printime.cli.print_image_page',
        ) as mock_print_image:
            cmd_print(args, config, printer)
        mock_print_image.assert_called_once()
        assert mock_print_image.call_args[0][2] == '/tmp/chart.png'

    def test_cmd_print_mermaid(self):
        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
        args = Namespace(
            test=None,
            image=None,
            mermaid='/tmp/flow.mmd',
            text=None,
            template=None,
            url=None,
            md=None,
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
        with patch('printime.services.diagram.mermaid_to_png', return_value='/tmp/flow.png') as mock_render, patch(
            'printime.cli.print_image_page',
        ) as mock_print_image:
            cmd_print(args, config, printer)
        assert mock_render.call_count == 1
        mock_print_image.assert_called_once()
        assert mock_print_image.call_args[0][2] == '/tmp/flow.png'

    def test_cmd_print_md_with_mermaid_renders_diagram(self):
        from printime.cli import cmd_print

        printer = MagicMock()
        config = {'printer': {'width': 48, 'paper_width_pixels': 576}}
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'diagram_flow.md')
        args = Namespace(
            test=None,
            image=None,
            mermaid=None,
            text=None,
            template=None,
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
        with patch('printime.cli.print_segments') as mock_segments, patch(
            'printime.cli.finish_job',
        ):
            cmd_print(args, config, printer)
        mock_segments.assert_called_once()
        context = mock_segments.call_args[0][3]
        types = [seg['type'] for seg in context['segments']]
        assert 'mermaid' in types
        assert 'qr' in types


class TestDiagramTemplate:
    def test_diagram_template_preview(self):
        from printime.preview import render_template_preview

        rendered = render_template_preview(
            'diagram',
            {'title': 'Architecture', 'caption': 'v1', 'mermaid': 'graph TD\n  A --> B'},
            width=48,
        )
        assert 'Architecture' in rendered
        assert 'v1' in rendered
        assert '[diagram]' in rendered.lower() or 'DIAGRAM' in rendered
