# Agent Protocol

Printime creates physical output, so previews are the default safety step for agents.

## Safe Print Workflow

1. Run `printime doctor` if this is first use, the printer changed, or printing failed.
2. Build the exact print command with `--preview`.
3. Read the preview output.
4. Check title, body order, QR density, Unicode, and `[CUT]`.
5. Print with `--yes` only when the user approved, explicitly asked for immediate print, or the job is trusted automation.

```bash
printime print notes.md --preview
printime print notes.md --yes
```

`[CUT]` is a preview marker only. It is not printed as text.

## Programmatic Preview Capture

Use this when an agent needs to inspect a preview before deciding whether to print:

```python
from printime.preview_capture import capture_cli_preview, read_preview

cap = capture_cli_preview(["print", "ticket.pdf", "--preview", "--yes"])
print(read_preview(cap["preview"]))
```

For template contexts:

```python
from printime.preview_capture import render_and_summarize, read_preview

result = render_and_summarize("ticket", context, config)
print(read_preview(result["preview"]))
```

## What to Check

- Title block is present when expected.
- Body sections are in source order.
- Checkboxes render as `[ ]` or `[X]`.
- QR codes are not overly dense; shorten very long URLs.
- Portuguese accents render in preview; set printer encoding if paper output garbles them.
- `[CUT]` appears unless `--no-cut` was requested.

## When `--yes` Is Appropriate

Use `--yes` for:

- User-confirmed print after preview.
- "Print now" requests where the user explicitly wants physical paper.
- Cron jobs or trusted automation.
- Capturing a non-interactive preview in scripts with `--preview --yes`.

Do not add `--yes` just to avoid reading the preview.
