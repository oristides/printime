# Agent Protocol

**This file contains:** programmatic preview capture (`capture_cli_preview`, `render_and_summarize`) and a pre-print inspection checklist.

Preview/print rules and when to use `--yes` are in [SKILL.md](../SKILL.md) §2.

## Programmatic Preview Capture

```python
from printime.preview_capture import capture_cli_preview, read_preview

cap = capture_cli_preview(["print", "ticket.pdf", "--preview"])
print(read_preview(cap["preview"]))
```

Template contexts:

```python
from printime.preview_capture import render_and_summarize, read_preview

result = render_and_summarize("ticket", context, config)
print(read_preview(result["preview"]))
```

## What to Check in Preview

- Title block present when expected.
- Body sections in source order; checkboxes as `[ ]` / `[X]`.
- QR codes not overly dense — shorten URLs over ~300 chars.
- Accents readable in preview; if paper garbles them, set `encoding: cp860` in `config/printer.yaml`.
- `[CUT]` appears unless `--no-cut` was requested.
