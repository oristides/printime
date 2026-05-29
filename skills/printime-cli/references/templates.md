# Templates (internal)

Agents use **intent commands**, not template names.

| Intent | Template |
| ------ | -------- |
| `note` | note |
| `checklist` | checklist |
| `task` | task |
| `message` | message |
| `email` | email |
| `url` | note (auto from article) |
| `ticket` | ticket |

## Checklist

```bash
printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry"
```

## Task / note / message

```bash
printime task --body "comer arroz hoy"
printime note --body "..."
printime message --title "Alert" --body "..."
```

Legacy files with `template:` frontmatter: `printime print file.md`
