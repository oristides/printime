# Printing Workflows

Prefer templates and `--preview` first. Add `--yes` only after approval or for trusted automation.

## Formatted Note

Use `note` for ordinary notes. It prints the title, optional caption, automatic `YYYY-MM-DD HH:MM` datetime, content, priority, and tags.

```bash
printime print --template note \
  --title "Today" \
  --content "Finish report, gym at 6pm" \
  --preview
```

## Checklist

Use a template/context file for structured checklists:

```yaml
title: Shopping
items:
  - text: Milk
    checked: false
  - text: Bread
    checked: true
```

```bash
printime print --template checklist --file shopping.yaml --preview
```

## Markdown File

```bash
printime print notes.md --preview
printime print examples/oriel-mandates.md --preview
printime print examples/diagram_flow.md --preview
printime print --md notes.md --template document --preview
```

Markdown can include YAML frontmatter, checkboxes, tables, mermaid fences, inline QR fences, and ASCII art fences. Tables are rendered as compact receipt columns in both preview and paper output. See [templates.md](templates.md).

## Enriched Markdown Text

Use `--markdown --text` for quick enriched content, but prefer `.md` files for anything reusable.

```bash
printime print --markdown --text $'# Today\n\n- [ ] Ship docs\n\n| Item | Status |\n| --- | --- |\n| Tables | Clean |' --preview
printime print --markdown --text $'```slant --center\nhello world\n```' --preview
```

ASCII art can also be printed directly:

```bash
printime print --ascii "hello" --ascii-font slant --center --preview
printime ascii-fonts
```

ASCII art font choices are limited to `pagga`, `avatar`, `bulbhead`, `banner`, and `slant` for reliable 48-column receipts.

## Google Calendar Agenda

```bash
printime agenda --today --preview
printime agenda --days 7 --preview
printime agenda --next-week --preview
```

Agenda prints the generated datetime below the title and includes event locations and notes/details when present.

## Standalone QR

```bash
printime print --qr "https://example.com"
printime print --qr "https://example.com" --qr-size 10
printime print --qr "https://example.com" --show-link
printime print --qr 'WIFI:T:WPA;S:Guest;P:password;;'
```

Long URLs make dense QR codes. Shorten URLs over about 300 characters.

## Web Articles

```bash
printime print --url "https://example.com/article" --preview
printime print --url "https://example.com/article" --max-chars 3000 --preview
printime print --url "https://example.com/article" --max-chars 0 --preview
```

Article printing extracts readable content and includes link QR segments. It works best with regular article pages and may fail on paywalls or heavily scripted sites.

## Ticket PDFs

Install ticket extras first:

```bash
pipx install -e ~/Documents/repos/random_projects/printime[all] --force
sudo apt install libzbar0
```

Print either positional `.pdf` or `--ticket`:

```bash
printime print ~/Downloads/ticket.pdf --preview
printime print --ticket ~/Downloads/ticket.pdf --preview
```

The ticket workflow extracts QR codes and barcodes in order, then renders the `ticket` template.

## Images

```bash
printime print --image photo.png --preview
```

Use images sized for the printer width where possible. 80mm paper is usually `576` pixels wide at 203dpi.

## Mermaid Diagrams

```bash
printime print --mermaid flow.mmd --preview
```

Requires Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Markdown files can also include ` ```mermaid ` fences.

## Plain Text Fallback

Plain text has no template title bar and no automatic datetime. Use it only for raw slips.

```bash
printime print --text "Hello world"
printime print --text "URGENT" --bold --center
printime print --text "No cut" --no-cut
```

For markdown passed inline, use `--markdown`, but prefer a template or markdown file for reusable output.
