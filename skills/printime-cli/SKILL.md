---
name: printime-cli
description: >-
  Use when operating the Printime CLI, ESC/POS thermal printers, notes, checklists,
  tasks, messages, QR codes, URLs, ticket PDFs, or integrations (Anytype, Keep, Calendar).
metadata:
  repository: ~/Documents/repos/random_projects/printime
  package: printime
  primaryConfig: config/printer.yaml
  primaryEnv: .env
references:
  - references/install.md
  - references/commands.md
  - references/printing.md
  - references/templates.md
  - references/integrations.md
  - references/troubleshooting.md
---

# Printime CLI

Thermal printer CLI for **80mm / 48-column** receipt printers.

---

## 1 · Setup (once per session)

```bash
(command -v printime >/dev/null && printime --version) || \
  pipx install -e ~/Documents/repos/random_projects/printime[all] --force
printime doctor
```

---

## 2 · Output mode

| You run | Result |
|---|---|
| `printime <intent> …` | **Terminal preview** (default) |
| `printime <intent> … --print` | **Paper** |

No `--preview` flag on intent commands. Preview is automatic.

**Only add `--print` when the user asks for paper now** (e.g. “on paper”, “imprimir no papel”, “print now”).

---

## 3 · Intent commands (pick one)

| User wants | Command |
|---|---|
| Todo / checkbox list | `printime checklist --items "A\|B::done"` |
| Single task card | `printime task --body "…"` |
| Quick memo | `printime note --body "…"` |
| Short alert | `printime message --body "…"` |
| Email summary | `printime email --body "…"` |
| Web article | `printime url "https://…"` |
| QR code | `printime qr "https://…"` |
| Ticket PDF | `printime ticket path/to.pdf` |
| Image | `printime image photo.png` |
| ASCII banner | `printime ascii "hello"` |
| Markdown **file** | `printime print notes.md` |
| Inline markdown | `printime print --markdown --text "…"` (use `\n` for line breaks) |
| Anytype page | `printime anytype print "Title"` |
| Keep note | `printime keep print "URL or ID"` |
| Calendar | `printime agenda --today` |

---

## 4 · `--title` (optional)

Omit `--title` → slip header is the **template name**: `Task`, `Note`, `Checklist`, `Message`, `Email`, …

Add `--title` only when the user names the list or slip:

| User implies | `--title` |
|---|---|
| lista de compras | `Compras` |
| weekly todos | `Weekly` |
| checklist del viaje | `Viaje` |
| print tasks: | `Tasks` |
| resumo do email | `Resumo` |
| quick memo / call dentist | omit (default `Note`) or `Memo` if user says “memo” |
| alert | `Alert` |

---

## 5 · Required vs optional (by intent)

| Intent | Required | Optional |
|---|---|---|
| `note` | `--body` (or `--file`) | `--title` (default Note), `--caption`, `--print` |
| `task` | `--body` (or `--file`) | `--title` (default Task), `--due`, `--done`, `--caption`, `--print` |
| `message` | `--body` (or `--file`) | `--title` (default Message), `--caption`, `--print` |
| `email` | `--body` (or `--file`) | `--title` (default Email), `--caption`, `--print` |
| `checklist` | `--items` (or `--file` with items) | `--title` (default Checklist), `--body` (intro text above list), `--caption`, `--print` |
| `url` | `TARGET` URL | `--print`, `--max-chars`, `--link-qr` |
| `qr` | `TARGET` payload | `--print`, `--qr-size`, `--show-link` |
| `ticket` | `TARGET` PDF path | `--print` |
| `image` | `TARGET` image path | `--title`, `--caption`, `--print` |
| `ascii` | `TARGET` text | `--ascii-font`, `--center`, `--print` |

Also written in:
- **`printime <intent> --help`** — flag lines (`optional; default: …`) + **Examples** epilog at bottom
- **`printime --help`** — `--title is optional` + disambiguation block

### Flag notes

| Flag | Use |
|---|---|
| `--title` | Optional slip header (default: template name) |
| `--body` | Main text; on **checklist** optional intro above the list (address, notes, …) |
| `--caption` | Optional subtitle under the title |
| `--items` | **Checklist only** — pipe-separated: `Milk\|Bread::done` |
| `--print` | Send to printer (default is preview) |
| `--no-cut` | Skip paper cut |

Checklist **checked** item: append `::done` or `::checked` to the **short item label** (e.g. `Bread::done`).

Use the marker word the user said:

| User says | Marker |
|---|---|
| done / já comprei / listo | `::done` |
| checked | `::checked` |

---

## 6 · Disambiguation

| User says | Run | Not |
|---|---|---|
| "print task …" / "tarea …" (one thing) | `printime task --body "…"` | checklist |
| "print tasks:" / "lista de compras:" (list) | `printime checklist --items "…"` | task |
| "tarea para mañana: X" | `printime task --body "X"` | `--title` (drop “para mañana” prefix) |
| "print article / link / matéria" + URL | `printime url "https://…"` | qr |
| "QR" / "escanear" / "scannable" | `printime qr "…"` | url |
| "resumo do email: …" | `printime email --title Resumo --body "…"` | message |

---

## 7 · Examples

**Checklist — 6 items** (mixed done/checked, contextual `--title`):

```bash
printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry"
```

| Item | Marker | Why |
|---|---|---|
| `gym`, `call mom`, `dentist`, `laundry` | (none) | still todo |
| `groceries::done` | `::done` | user said "done" |
| `pay rent::checked` | `::checked` | user said "checked" |

Grocery list — intro text + items:

```bash
printime checklist --title Compras --body "Rua Example 123" --caption "Entrega sábado" \
    --items "arroz|feijão|pão::done"
```

Grocery list — items only (6 items, one bought):

```bash
printime checklist --title Compras --items "arroz|feijão|café|leite|pão::done|açúcar"
```

Other intents:

```bash
printime checklist --title Tasks --items Votar
printime task --body "comer arroz hoy"
printime note --body "Call dentist"
printime message --title Alert --body "Printer ready"
printime email --title Resumo --body "Reunião cancelada — remarcar sexta 15h"
printime url "https://example.com/article"
printime qr "https://example.com"
printime print --markdown --text "# Sprint\n\n- fix bug\n- ship"
printime print notes.md
```

Print after preview:

```bash
printime checklist --title Weekly --items "gym|groceries::done|call mom|pay rent::checked|dentist|laundry" --print
```

---

## 8 · Natural language → command

| User says | Run |
|---|---|
| "print task comer arroz hoy" | `printime task --body "comer arroz hoy"` |
| "print tasks: Votar" | `printime checklist --title Tasks --items Votar` |
| "print my weekly todos: gym, groceries done, call mom, pay rent checked, dentist, laundry" | `printime checklist --title Weekly --items "gym\|groceries::done\|call mom\|pay rent::checked\|dentist\|laundry"` |
| "imprime el ultimo mensaje…" | `printime message --title Mensaje --body "<text from chat>"` |
| "imprime este link https://…" | `printime url "https://…"` |
| "imprima o arquivo foo.md" | `printime print foo.md` |

---

## 9 · Guard-rails

| Wrong | Right |
|---|---|
| `printime print --template checklist …` | `printime checklist …` |
| `--content` on intents | `--body` |
| `--preview` on intents | omit (preview is default) |
| `--print` without user asking for paper | omit |
| `printime print --url …` | `printime url …` |
| Long phrase as item label + marker | short label + `::done` (e.g. `cargador::done`) |

Legacy `printime print` is for **markdown files** and **inline markdown** only.

---

## 10 · References

| Need | File | Notes |
|---|---|---|
| Install / config | [install.md](references/install.md) | pipx, printer.yaml, extras |
| Flags / HTTP API | [commands.md](references/commands.md) | intent-first; legacy `print` at bottom |
| Checklist / workflows | [printing.md](references/printing.md) | `--items`, 6-item examples |
| Template mapping | [templates.md](references/templates.md) | intent → template (internal) |
| Integrations | [integrations.md](references/integrations.md) | anytype, keep, agenda (still use `--preview` there) |
| Troubleshooting | [troubleshooting.md](references/troubleshooting.md) | doctor, encoding, USB |
