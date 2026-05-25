#!/usr/bin/env python3
"""Tests for URL fetch link preservation and link QR segments."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


SAMPLE_WITH_LINKS = """
<html><head><title>Blog Post</title></head><body>
<article>
<p>Read this <a href="https://example.com/deck">annual deck</a> for more.</p>
<p><a href="https://colossus.com/article/scott-wu/"><span></span></a></p>
<p>Plain mention https://bare.example/path ends here.</p>
</article>
</body></html>
"""


class TestFetchUrlLinks:
    def test_anchors_to_markdown(self):
        from printime.services.fetch_url import article_html_to_text
        from printime.services.link_qr import normalize_document_links

        md = normalize_document_links(
            '<p>See <a href="https://foo.com/x">Foo site</a> now.</p>'
        )
        assert '[Foo site](https://foo.com/x)' in md
        text = article_html_to_text(
            '<p>Card <a href="https://bar.com/y"><div></div></a> end.</p>'
        )
        assert '[bar.com](https://bar.com/y)' in text

    def test_url_to_context_link_qr_segments(self):
        from printime.services import fetch_url

        original = fetch_url.fetch_html
        fetch_url.fetch_html = lambda url: SAMPLE_WITH_LINKS
        try:
            ctx = fetch_url.url_to_context(
                'https://example.com/post',
                width=48,
                max_chars=None,
                link_qr=True,
            )
        finally:
            fetch_url.fetch_html = original

        assert ctx['template'] == 'document'
        qr_data = [s['data'] for s in ctx['segments'] if s.get('type') == 'qr']
        assert 'https://example.com/deck' in qr_data
        assert 'https://colossus.com/article/scott-wu/' in qr_data
        assert 'https://example.com/post' in qr_data  # main_url QR

    def test_url_preview_renders_link_qrs(self):
        from printime.services import fetch_url
        from printime.preview import render_template_preview

        original = fetch_url.fetch_html
        fetch_url.fetch_html = lambda url: SAMPLE_WITH_LINKS
        try:
            ctx = fetch_url.url_to_context(
                'https://example.com/post',
                width=48,
                max_chars=None,
                link_qr=True,
            )
            preview = render_template_preview(ctx['template'], ctx, width=48)
        finally:
            fetch_url.fetch_html = original

        assert '██' in preview
        assert '[QR]' in preview
        assert preview.count('[QR]') >= 2
