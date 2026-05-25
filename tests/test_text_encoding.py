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

    def test_cp860_differs_from_cp850_for_tilde_a(self):
        from printime.text_encoding import encode_for_printer

        assert encode_for_printer('ã', 'cp850') != encode_for_printer('ã', 'cp860')
        assert encode_for_printer('í', 'cp850') == encode_for_printer('í', 'cp860')
        assert encode_for_printer('ç', 'cp850') == encode_for_printer('ç', 'cp860')

    def test_escpos_select_code_page(self):
        from printime.text_encoding import escpos_select_code_page

        assert escpos_select_code_page('cp860') == b'\x1b\x74\x03'
        assert escpos_select_code_page('cp850') == b'\x1b\x74\x02'
        assert escpos_select_code_page('ascii') is None

    def test_cp860_keeps_portuguese(self):
        from printime.text_encoding import encode_for_printer, decode_for_display

        raw = encode_for_printer('ação coração', 'cp860')
        assert decode_for_display(raw, 'cp860') == 'ação coração'

    def test_preview_keeps_portuguese(self):
        from printime.preview import normalize_preview_text

        assert 'ã' in normalize_preview_text('São Paulo')

    def test_sanitize_printer_text_cp850(self):
        from printime.preview import sanitize_printer_text

        assert sanitize_printer_text('São Paulo') == 'São Paulo'
        assert sanitize_printer_text('• item') == '* item'
