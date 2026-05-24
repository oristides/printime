#!/usr/bin/env python3
"""Capture and summarize terminal previews for agent self-check."""

from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, List, Optional


def strip_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


def parse_preview_lines(preview_text: str) -> List[str]:
    """Extract inner content from bordered preview lines."""
    lines = []
    for raw in strip_ansi(preview_text).splitlines():
        if raw.startswith('|') and raw.endswith('|'):
            lines.append(raw[1:-1].rstrip())
        elif raw.strip():
            lines.append(raw.rstrip())
    return lines


def summarize_preview(preview_text: str) -> Dict[str, Any]:
    """Structured summary for agents to verify layout without re-parsing manually."""
    plain = strip_ansi(preview_text)
    inner = parse_preview_lines(preview_text)
    qr_blocks = plain.count('██')
    return {
        'line_count': len(inner),
        'has_cut_guide': '[CUT]' in plain,
        'has_title_block': '====' in plain.replace('=', '') or bool(re.search(r'\|={10,}', plain)),
        'qr_module_lines': sum(1 for line in inner if '██' in line),
        'qr_estimated_modules': qr_blocks // 2,
        'contains_unicode': any(ord(c) > 127 for c in plain),
        'sample_lines': inner[:8] + (['...'] if len(inner) > 8 else []),
        'issues': _detect_issues(inner, plain),
    }


def _detect_issues(inner: List[str], plain: str) -> List[str]:
    issues: List[str] = []
    if '' in inner and inner.count('') > len(inner) * 0.5:
        pass
    if re.search(r'Ã[£¡§]', plain) or 'S?o' in plain:
        issues.append('mojibake_or_ascii_fallback_detected')
    if '[QR]' in plain and '██' not in plain:
        issues.append('qr_placeholder_without_ascii_render')
    if not inner:
        issues.append('empty_preview')
    return issues


def render_and_summarize(
    template_name: str,
    context: dict,
    config: Optional[dict] = None,
    *,
    width: int = 48,
) -> Dict[str, Any]:
    """Render template preview and return text + summary for agent verification."""
    from printime.preview import render_template_preview

    if config is None:
        from printime.cli import load_config
        config = load_config()

    text = render_template_preview(template_name, context, width=width)
    summary = summarize_preview(text)
    return {'preview': text, 'summary': summary, 'ok': not summary['issues']}


def capture_cli_preview(argv: List[str], *, cwd: Optional[str] = None) -> Dict[str, Any]:
    """Run printime CLI with --preview --yes and capture stdout summary."""
    result = subprocess.run(
        ['printime', *argv],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    out = result.stdout
    return {
        'exit_code': result.returncode,
        'preview': out,
        'summary': summarize_preview(out),
        'stderr': result.stderr,
        'ok': result.returncode == 0 and not summarize_preview(out)['issues'],
    }


def read_preview(preview_text: str) -> str:
    """Human/agent readable digest of a preview."""
    s = summarize_preview(preview_text)
    lines = [
        f"lines={s['line_count']} qr_rows={s['qr_module_lines']} cut={s['has_cut_guide']}",
        f"unicode={s['contains_unicode']} issues={s['issues'] or 'none'}",
        '--- sample ---',
    ]
    lines.extend(s['sample_lines'])
    return '\n'.join(lines)
