#!/usr/bin/env python3
"""Tests for markdown enrichment and --markdown behavior."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestEnrich:
    def test_looks_like_markdown_detects_heading(self):
        from printime.services.enrich import looks_like_markdown

        assert looks_like_markdown('# Title\n\nBody')
        assert not looks_like_markdown('plain text only')

    def test_enrich_context_fields_parses_content(self):
        from printime.services.enrich import enrich_context_fields

        ctx = enrich_context_fields({'content': '# Hello\n\nWorld'}, width=48)
        assert 'content_lines' in ctx
        assert any('Hello' in line.text for line in ctx['content_lines'])

    def test_enrich_link_qr_builds_segments(self):
        from printime.services.enrich import enrich_context_fields

        ctx = enrich_context_fields(
            {'content': 'Read [blog](https://example.com/post) now.'},
            width=48,
            link_qr=True,
        )
        types = [s['type'] for s in ctx['segments']]
        assert 'qr' in types
        qr = next(s for s in ctx['segments'] if s['type'] == 'qr')
        assert qr['data'] == 'https://example.com/post'

    def test_markdown_to_context_link_qr(self):
        from printime.services.transform import markdown_to_context

        md = 'See [site](https://example.com) for more.'
        ctx = markdown_to_context(md, 'x.md', 48, link_qr=True)
        assert any(seg.get('type') == 'qr' for seg in ctx['segments'])
