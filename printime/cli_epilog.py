#!/usr/bin/env python3
"""Shared --help epilogs for printime CLI."""

from __future__ import annotations

TEMPLATE_NAMES = (
    'note',
    'checklist',
    'document',
    'diagram',
    'task',
    'jira',
    'message',
    'email',
    'receipt',
    'heading',
    'agenda',
    'equation',
    'ticket',
)

TEMPLATE_CHOICES_HELP = ', '.join(TEMPLATE_NAMES)

MAIN_EPILOG = """
Intent commands (preview by default; add --print for paper):

  printime note        --body "Call dentist"              # title → Note
  printime checklist   --items "Milk|Bread::done"         # title → Checklist
  printime task        --body "Buy milk"                  # title → Task
  printime message     --body "Printer ready"            # title → Message
  printime url         "https://example.com/article"
  printime qr          "https://example.com"

  --title is optional. Omit it to use the template name on the slip (Task, Note, …).
  Checklist checked items: append ::done or ::checked (e.g. Bread::done).

Pick the right intent:
  one thing to do       →  task --body "…"
  list / todos          →  checklist --items "A|B::done"
  web article / link    →  url "https://…"
  scannable QR code     →  qr "https://…"

Integrations:
  printime anytype print "Page title"
  printime keep print "https://keep.google.com/..."
  printime agenda --today

Ops:
  printime doctor --test-print
  printime list checklist            # template fields (optional)

Legacy: printime print … (markdown files, inline markdown)
"""

PRINT_EPILOG = """
Legacy print — prefer intent commands above.

  printime print notes.md
  printime print --markdown --text "# Title\\n\\n- item"
"""

INTENT_EPILOGS = {
    'note': """
Example:
  printime note --body "Call dentist tomorrow"

  --title optional (default: Note). --body required (the memo text).
""",
    'checklist': """
Examples:
  printime checklist --items "Milk|Bread::done|Eggs"
  printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry"
  printime checklist --title Compras --body "Rua Example 123" --caption "Entrega sábado" \\
      --items "arroz|feijão|pão::done"

  --items   required for a checkbox list (or use --file); pipe-separated; checked → ::done or ::checked
  --body    optional intro text above the list (address, notes, …)
  --caption optional subtitle under the title
  --title   optional (default: Checklist); use Compras, Weekly, Viaje when user names the list

  One single todo → use task --body instead.
""",
    'task': """
Example:
  printime task --body "comer arroz hoy"

  --title optional (default: Task). --body required (the one thing to do).
  Multiple items / todos → use checklist --items instead.
""",
    'message': """
Example:
  printime message --title Alert --body "Printer ready"

  --title optional (default: Message). Short alert slip.
""",
    'email': """
Example:
  printime email --title Resumo --body "Reunião cancelada — remarcar sexta 15h"

  --title optional (default: Email). Email summary slip.
""",
    'url': """
Example:
  printime url "https://example.com/article"

  Fetches and prints a web article. Not a QR code — use qr for scannable codes.
""",
    'qr': """
Example:
  printime qr "https://example.com"

  Standalone QR code to scan. Not a full article — use url to print page text.
""",
    'ticket': """
Example:
  printime ticket ~/Downloads/ticket.pdf

  Extracts QR/barcodes from a ticket PDF.
""",
    'image': """
Example:
  printime image photo.png --title "Receipt" --caption "March 2026"
""",
    'ascii': """
Example:
  printime ascii hello --center
""",
}
