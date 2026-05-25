# Hotkeys, shortcuts, and app integration

Printime is a **CLI-first** tool — for users, AI agents, and apps. The right workflow is always:

**detect content → correct `printime` command → `--preview` → print**

Do **not** use Ctrl+P to the raw **POS8370** CUPS queue (PDF garbage on thermal). Do **not** rely on a network print service — use commands below.

---

## Recommended workflow

```bash
printime <subcommand> … --preview    # see paper simulation
# confirm, then:
printime <subcommand> … --yes        # print without prompt
```

Agents should use **`--preview`** and read the output (see `preview_capture` in the skill).

---

## Desktop hotkeys (Linux)

Bind these in **Settings → Keyboard → Custom shortcuts**.

| Shortcut | Action | Command |
|----------|--------|---------|
| `Ctrl+Shift+P` | Anytype page (title in clipboard) | `~/Documents/repos/random_projects/printime/scripts/anytype-print.sh` |
| `Ctrl+Shift+U` | URL in clipboard → blog/article | `~/Documents/repos/random_projects/printime/scripts/print-url.sh` |
| `Ctrl+Shift+T` | Ticket PDF path in clipboard | `~/Documents/repos/random_projects/printime/scripts/print-ticket.sh` |

Scripts use **`--preview`** by default. Set `PRINTIME_YES=1` to skip confirmation.

### Anytype (included)

```bash
scripts/anytype-print.sh "Page title"
scripts/anytype-print.sh    # title from clipboard
```

Runs: `printime anytype print "…" --preview` (or `--yes` if `PRINTIME_YES=1`).

---

## Command cheat sheet by source

| You have… | Command |
|-----------|---------|
| Anytype page | `printime anytype print "Title" --preview` |
| Google Keep note URL | `printime keep print "https://keep.google.com/#NOTE/…" --preview` |
| Blog / article URL | `printime print --url 'https://…' --link-qr --preview` |
| Ticket PDF | `printime print --ticket ticket.pdf --preview` |
| Markdown file | `printime print notes.md --preview` |
| Jira (copy as markdown) | Save to `.md` or use `--template jira` + context file |
| Plain text | `printime print --text "…"` |
| Calendar week | `printime agenda --next-week --preview` |

---

## For applications and agents

### HTTP (automation)

```bash
printime serve --port 8080
```

**POST** `/print` with JSON — see [COMMANDS.md](COMMANDS.md#serve). Use on LAN or Tailscale only (no auth).

### Shell / Python

```bash
printime print --ticket "$PDF" --preview --yes
printime print --url "$URL" --preview --yes
```

```python
from printime.preview_capture import capture_cli_preview, read_preview

cap = capture_cli_preview(['print', '--url', url, '--preview', '--yes'])
print(read_preview(cap['preview']))
```

### Why not Ctrl+P?

Apps send **PDF snapshots**. Printime templates need **structured input** (markdown, API, URL, PDF ticket path). Ctrl+P loses that unless you build a custom CUPS filter (not supported — use CLI instead).

---

## Clean up old CUPS “Printime” queue (if you installed it)

If you previously ran `printime service install`:

```bash
sudo lpadmin -x Printime
sudo rm -f /usr/local/lib/cups/filter/printime /usr/lib/cups/filter/printime
sudo rm -rf /usr/local/share/ppd/printime
sudo rm -f /etc/avahi/services/printime.service
rm -f ~/.config/printime/service-install.json
sudo systemctl try-reload-or-restart avahi-daemon
```

CLI printing is unaffected.

---

## Related

- [NATIVE.md](NATIVE.md) — Anytype shortcut setup
- [COMMANDS.md](COMMANDS.md) — full CLI
- [QUICKSTART.md](QUICKSTART.md) — first print
