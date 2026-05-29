# Printing Workflows

## Checklist

**6 items** (mixed done/checked):

```bash
printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry"
```

With intro text above the list:

```bash
printime checklist --title Compras --body "Rua Example 123" --caption "Entrega sábado" \
    --items "arroz|feijão|pão::done"
```

Separator: `|`. Checked: `::done` or `::checked`. Short item labels only — put the marker on the label, not a long phrase.

## Other intents

```bash
printime note --body "Call dentist"              # title → Note
printime task --body "comer arroz hoy"           # title → Task
printime message --title Alert --body "Printer ready"
printime url "https://example.com/article"
printime qr "https://example.com"
```

`--title` is optional; omit it to use the template name on the slip.

Default = preview. Add `--print` for paper.

## Ticket PDF

```bash
printime ticket ~/Downloads/ticket.pdf
```

## Images

```bash
printime image photo.png
```

Target **576 px** wide for 80mm paper.

## Markdown (legacy `print`)

Files and inline markdown only:

```bash
printime print notes.md
printime print --markdown --text "# Title\n\n- item"
```
