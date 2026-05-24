#!/usr/bin/env python3
"""Tests for printer text encoding."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestTextEncoding:
    def test_cp850_keeps_portuguese(self):
        from printime.text_encoding import encode_for_printer, decode_for_display

        raw = encode_for_printer('São Paulo', 'cp850')
        assert decode_for_display(raw, 'cp850') == 'São Paulo'

    def test_preview_keeps_portuguese(self):
        from printime.preview import normalize_preview_text

        assert 'ã' in normalize_preview_text('São Paulo')

    def test_sanitize_printer_text_cp850(self):
        from printime.preview import sanitize_printer_text

        assert sanitize_printer_text('São Paulo') == 'São Paulo'
        assert sanitize_printer_text('• item') == '* item'
