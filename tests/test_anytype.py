#!/usr/bin/env python3
"""Tests for Anytype page → print context conversion."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from printime.services.anytype import (
    detect_template,
    normalize_anytype_markdown,
    page_to_template_context,
)


class TestAnytypePageContext:
    def test_merges_body_text_with_checkbox_markdown(self):
        page = {
            'name': 'RETROSUM',
            'markdown': '- [x] eXEMPLO 2\n- [ ] DEDED',
            'body': 'Sprint went well overall.\nWatch scope creep.',
        }
        ctx = page_to_template_context(page, 48)
        assert ctx['template'] == 'checklist'
        assert 'Sprint went well' in ctx.get('content', '')
        assert len(ctx['items']) == 2

    def test_skips_empty_checkbox_lines(self):
        page = {
            'name': 'Tasks',
            'markdown': '- [x] Done\n- [x] \n- [ ] Todo',
        }
        ctx = page_to_template_context(page, 48)
        assert len(ctx['items']) == 2
        assert ctx['items'][0]['text'] == 'Done'

    def test_page_name_overrides_body_heading_title(self):
        page = {
            'name': 'Login Flow',
            'markdown': '# Headin1\n\nHello world',
        }
        ctx = page_to_template_context(page, 48)
        assert ctx['title'] == 'Login Flow'

    def test_normalizes_escaped_fences_and_tight_checkboxes(self):
        raw = """# Headin1
-[x] Bread
\\`\\`\\`qr --qr-size 13 --center
"https://example.com"
\\`\\`\\`
"""
        normalized = normalize_anytype_markdown(raw)
        assert '- [x] Bread' in normalized
        assert '```qr --qr-size 13 --center' in normalized
        assert '\\`' not in normalized

    def test_pasted_login_flow_uses_document_template(self):
        page = {
            'name': 'Login Flow',
            'markdown': """# Headin1
## heading 2
### heading 3

Hello wordl

- [ ] Milkssdsd
-[x] Bread
- [ ] Eggs

\\`\\`\\`mermaid
graph TD
  A --> B
\\`\\`\\`

\\`\\`\\`qr --qr-size 13 --center
"https://www.youtube.com/watch?v=7B0IuevRuUU"
\\`\\`\\`
""",
        }
        ctx = page_to_template_context(page, 48)
        assert ctx['title'] == 'Login Flow'
        assert ctx['template'] == 'document'
        assert any(seg.get('type') == 'qr' for seg in ctx.get('segments', []))
        assert any(seg.get('type') == 'mermaid' for seg in ctx.get('segments', []))
        assert len(ctx['items']) == 3
        assert ctx['items'][1]['checked'] is True

    def test_detect_template_respects_context_template(self):
        page = {'name': 'Login Flow', 'object': {'name': 'Login Flow'}}
        context = {'template': 'document', 'items': [{'text': 'x', 'checked': False}]}
        assert detect_template(page, context) == 'document'

    def test_anytype_table_content_is_rendered_cleanly(self):
        page = {
            'name': 'RETROSUM',
            'markdown': (
                '|| de   <br> | dsd   <br> | 123   <br> | das     |\n'
                '|<br> |                                          |\n'
                '||:----------|:-----------|:-----------|:--------|\n'
                '|---|                                            |\n'
                '|| ss   <br> |       <br> |   a   <br> | das     |\n'
                '|<br> |                                          |\n'
                '|| wd   <br> |  sa   <br> | 312   <br> | 123     |'
            ),
        }

        ctx = page_to_template_context(page, 48)
        content = ctx.get('content', '')

        assert 'de' in content and 'dsd' in content
        assert 'ss' in content and 'das' in content
        assert '<br>' not in content
        assert '||' not in content
