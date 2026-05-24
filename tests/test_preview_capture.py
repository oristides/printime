#!/usr/bin/env python3
"""Tests for preview capture / agent self-read."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestPreviewCapture:
    def test_summarize_detects_qr_and_unicode(self):
        from printime.preview_capture import summarize_preview

        preview = """|================================================|
|São Paulo                                       |
|[QR] (size=10)                                   |
|  ██████  ██  ██████                             |
|================================================|"""
        s = summarize_preview(preview)
        assert s['qr_module_lines'] >= 1
        assert s['contains_unicode']
        assert s['issues'] == []

    def test_read_preview_digest(self):
        from printime.preview_capture import read_preview

        text = read_preview("|São Paulo\n|  ████")
        assert 'unicode=True' in text
        assert 'São Paulo' in text

    def test_render_and_summarize_ticket(self):
        from printime.preview_capture import render_and_summarize
        from printime.services.tickets import pdf_to_ticket_context

        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'tickets-pdf', '355UPARHGU2.pdf')
        if not os.path.isfile(path):
            return
        ctx = pdf_to_ticket_context(path, 48)
        ctx['paper_width_pixels'] = 576
        result = render_and_summarize('ticket', ctx)
        assert result['summary']['qr_module_lines'] >= 1
        assert 'preview' in result
