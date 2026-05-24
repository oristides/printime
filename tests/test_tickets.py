#!/usr/bin/env python3
"""Tests for ticket PDF extraction."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

TICKETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'tickets-pdf')


def _pdf(name: str) -> str:
    return os.path.join(TICKETS_DIR, name)


@pytest.mark.skipif(not os.path.isdir(TICKETS_DIR), reason='ticket examples missing')
class TestTicketPdf:
    def test_extract_codes_from_meus_ingressos(self):
        from printime.services.tickets import extract_codes_from_pdf

        path = _pdf('meus-ingressos.pdf')
        if not os.path.isfile(path):
            pytest.skip('meus-ingressos.pdf not found')
        codes = extract_codes_from_pdf(path)
        data = [c.data for c in codes if c.data]
        assert '1200798682009' in data
        assert '1392016206187' in data

    def test_extract_codes_preserves_page_order(self):
        from printime.services.tickets import extract_codes_from_pdf

        path = _pdf('meus-ingressos.pdf')
        if not os.path.isfile(path):
            pytest.skip('meus-ingressos.pdf not found')
        codes = extract_codes_from_pdf(path)
        pages = [c.page for c in codes]
        assert pages == sorted(pages)

    def test_pdf_to_ticket_context_has_segments(self):
        from printime.services.tickets import pdf_to_ticket_context

        path = _pdf('Ticket-160865407.pdf')
        if not os.path.isfile(path):
            pytest.skip('Ticket-160865407.pdf not found')
        ctx = pdf_to_ticket_context(path, 48)
        assert ctx['template'] == 'ticket'
        assert ctx['title']
        types = [s['type'] for s in ctx['segments']]
        assert 'qr' in types

    def test_ticket_preview_contains_ascii_qr(self):
        from printime.preview import render_template_preview
        from printime.services.tickets import pdf_to_ticket_context

        path = _pdf('355UPARHGU2.pdf')
        if not os.path.isfile(path):
            pytest.skip('355UPARHGU2.pdf not found')
        ctx = pdf_to_ticket_context(path, 48)
        out = render_template_preview('ticket', ctx)
        assert '█' in out
        assert 'UZAAE2RV2F' in out or any(
            seg.get('data') == 'UZAAE2RV2F' for seg in ctx['segments'] if seg.get('type') == 'qr'
        )

    def test_cli_ticket_preview(self, capsys):
        from printime.cli import main

        path = _pdf('355UPARHGU2.pdf')
        if not os.path.isfile(path):
            pytest.skip('355UPARHGU2.pdf not found')
        sys.argv = ['printime', 'print', '--ticket', path, '--preview', '--yes']
        main()
        out = capsys.readouterr().out
        assert '█' in out
