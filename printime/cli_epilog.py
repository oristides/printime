#!/usr/bin/env python3
"""Shared --help epilogs for printime CLI."""

from __future__ import annotations

MAIN_EPILOG = """
Templates (see: printime list, printime list <name>):
  note, checklist, document, diagram, task, jira, message,
  receipt, heading, agenda, equation, ticket

Examples:
  printime print --text "Hello"
  printime print --markdown --text "# Title\\n\\nBody" --preview
  printime print notes.md --preview
  printime print examples/diagram_flow.md --preview
  printime print --url 'https://example.com/post' --link-qr --preview
  printime print --ticket examples/tickets-pdf/Ticket.pdf --preview
  printime print --qr "https://example.com"
  printime anytype print "Page title" --preview
  printime agenda --next-week --preview
  printime doctor --test-print

Markdown mini-syntax (.md files, --markdown, template content):
  # H1   ## H2   ### H3   **bold**   - bullets   - [ ] checkboxes
  [label](https://url)  + --link-qr  → label + mini QR
  ```qr --qr-size 8 --center
  https://example.com
  ```
"""

PRINT_EPILOG = """
Examples:
  printime print --text "Plain line"
  printime print --markdown --text "# Shop\\n- [ ] Milk" --preview
  printime print note.md --preview
  printime print --url 'https://blog.example/post' --link-qr --preview
  printime print --ticket ticket.pdf --preview
  printime print --qr "https://example.com" --qr-size 10
"""
