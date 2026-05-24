#!/usr/bin/env python3
"""Tests for ASCII QR preview rendering."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestPreviewQr:
    def test_render_qr_ascii_produces_dark_blocks(self):
        from printime.preview_qr import render_qr_ascii

        lines = render_qr_ascii('https://example.com', paper_cols=46)
        assert lines
        assert any('█' in line for line in lines)

    def test_render_qr_ascii_respects_width(self):
        from printime.preview_qr import render_qr_ascii

        for line in render_qr_ascii('hello', paper_cols=40, qr_size=8):
            assert len(line) <= 40

    def test_larger_qr_size_yields_larger_preview(self):
        from printime.preview_qr import render_qr_ascii

        small = render_qr_ascii('https://example.com', qr_size=4, paper_cols=48)
        large = render_qr_ascii('https://example.com', qr_size=10, paper_cols=48)
        assert max(len(line) for line in large) >= max(len(line) for line in small)

    def test_segment_preview_shows_ascii_qr(self):
        from printime.preview import _render_segments_preview

        out = _render_segments_preview({
            'title': 'Test',
            'segments': [{'type': 'qr', 'data': 'https://example.com', 'qr_size': 8, 'center': True}],
        })
        assert '█' in out
        assert '[QR]' in out
