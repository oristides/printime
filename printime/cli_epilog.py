#!/usr/bin/env python3
"""Shared --help epilogs for printime CLI."""

from __future__ import annotations

MAIN_EPILOG = """
Templates (see: printime list, printime list <name>):
  note, checklist, document, diagram, task, jira, message, email,
  receipt, heading, agenda, equation, ticket

Examples:
  printime print --template note --title "Today" \\
    --content "Ship docs" --preview
  printime print --template message --title "Alert" \\
    --content "Printer ready" --preview
  printime print examples/email.md --preview
  printime print notes.md --preview
  printime print examples/diagram_flow.md --preview
  printime print --url 'https://example.com/post' --link-qr --preview
  printime print --ticket examples/tickets-pdf/Ticket.pdf --preview
  printime print --qr "https://example.com"
  printime print --ascii "hello" --ascii-font slant --center --preview
  printime ascii-fonts
  printime anytype print "Page title" --preview
  printime agenda --today --preview
  printime agenda --days 7 --preview
  printime doctor --test-print

Markdown mini-syntax (.md files, --markdown, template content):
  # H1   ## H2   ### H3   **bold**   - bullets   - [ ] checkboxes
  [label](https://url)  + --link-qr  → label + mini QR
  ```qr --qr-size 8 --center
  https://example.com
  ```
  ```slant --center
  hello
  ```
"""

PRINT_EPILOG = """
Examples:
  printime print --template note --title "Today" \\
    --content "Ship docs" --preview
  printime print --template message --title "Alert" \\
    --content "Printer ready" --preview
  printime print examples/email.md --preview
  printime print note.md --preview
  printime print --url 'https://blog.example/post' --link-qr --preview
  printime print --ticket ticket.pdf --preview
  printime print --qr "https://example.com" --qr-size 10
  printime print --ascii "hello" --ascii-font slant --center --preview
  printime ascii-fonts
  printime print --text "Plain line"
"""
