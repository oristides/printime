# Printing Workflows

**This file contains:** checklist `--items` syntax, ticket PDF, image width, plain-text caveat.

Command examples: [SKILL.md](../SKILL.md) §5. Flags: [commands.md](commands.md).

## Checklist

```bash
printime print --template checklist --title "Market" \
  --items "Milk|Bread::x|Eggs|Butter|Cheese|Coffee::x" --preview
```

| Token | Printed |
| ----- | ------- |
| `Milk` | `[ ] Milk` |
| `Bread::x` | `[X] Bread` |
| `Deploy: staging` | `[ ] Deploy: staging` |

Separator: `|`. Checked: `::x`, `::checked`, `::done`. Optional `--content` for prose above the list.

## Ticket PDF

Both forms are equivalent after ticket extras are installed (see [install.md](install.md)):

```bash
printime print ~/Downloads/ticket.pdf --preview
printime print --ticket ~/Downloads/ticket.pdf --preview
```

## Images

`--image` scales to printer width. Target **576 px** wide for 80mm / 203 dpi.

## Plain Text vs Template

`--text` alone has no title bar or datetime — last resort. Prefer `--template note` or `--items` for checklists.
