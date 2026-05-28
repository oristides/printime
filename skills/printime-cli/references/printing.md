# Printing Workflows

**This file contains:** non-obvious details not covered by flag tables — checklist YAML shape, ticket PDF invocation, image width, plain-text vs template.

Command examples and the decision tree are in [SKILL.md](../SKILL.md) §3 and §5. Flags: [commands.md](commands.md).

## Checklist YAML Shape

`--template checklist --file` expects:

```yaml
title: Shopping
items:
  - text: Milk
    checked: false
  - text: Bread
    checked: true
```

## Ticket PDF

Both forms are equivalent after ticket extras are installed (see [install.md](install.md)):

```bash
printime print ~/Downloads/ticket.pdf --preview
printime print --ticket ~/Downloads/ticket.pdf --preview
```

Extracts QR codes and barcodes in document order, then renders the `ticket` template.

## Images

`--image` scales to printer width. Target **576 px** wide for 80mm / 203 dpi; narrower sources are upscaled, wider are shrunk.

## Plain Text vs Template

`--text` alone has **no** title bar, automatic datetime, or template fields — last resort for raw slips. Prefer `--template note` (or a `.md` file) for anything you might print again.
