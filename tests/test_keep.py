#!/usr/bin/env python3
"""Tests for Google Keep integration."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestKeepParsing:
    def test_parse_note_id_from_url(self):
        from printime.services.keep import parse_note_id

        url = 'https://keep.google.com/#NOTE/1_hjNNZwcXIdKUqjQ8stzfreTy0BgG1flZEjaxBiflc6qMSbM6ihWDTigNaOZFmVCq3d1'
        assert parse_note_id(url) == '1_hjNNZwcXIdKUqjQ8stzfreTy0BgG1flZEjaxBiflc6qMSbM6ihWDTigNaOZFmVCq3d1'

    def test_parse_note_id_raw(self):
        from printime.services.keep import parse_note_id

        assert parse_note_id('abc123xyz789012345678901') == 'abc123xyz789012345678901'

    def test_note_to_markdown_checklist(self):
        from printime.services.keep import note_to_markdown

        item1 = MagicMock(text='Milk', checked=False)
        item2 = MagicMock(text='Bread', checked=True)
        note = MagicMock(title='Groceries', text='', items=[item1, item2])
        md = note_to_markdown(note)

        assert '# Groceries' in md
        assert '- [ ] Milk' in md
        assert '- [x] Bread' in md

    def test_note_to_context_offline(self):
        from printime.services import keep as keep_mod

        note = MagicMock()
        note.id = 'note123'
        note.title = 'Psicología'
        note.text = 'Notas em português com links https://example.com'
        note.items = None
        note.labels = None

        mock_keep = MagicMock()
        mock_keep.get.return_value = note

        with patch.object(keep_mod, 'connect_keep', return_value=mock_keep):
            ctx = keep_mod.note_to_context('note123', width=48, config={'printer': {'width': 48}})

        assert ctx['title'] == 'Psicología'
        assert 'source_url' in ctx
        assert any(seg.get('type') == 'qr' for seg in ctx.get('segments', []))
