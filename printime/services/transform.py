#!/usr/bin/env python3
"""
Transform Service - Convert markdown and other files to print template context.
"""

import os
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Optional, Dict, Any, List, Tuple

import yaml

CHECKBOX_RE = re.compile(r'^\s*-\s+\[([ xX])\]\s+(.*)$', re.MULTILINE)


def check_latex_tools() -> bool:
    has_pdflatex = subprocess.run(['which', 'pdflatex'], capture_output=True).returncode == 0
    has_pdftoppm = subprocess.run(['which', 'pdftoppm'], capture_output=True).returncode == 0
    return has_pdflatex and has_pdftoppm


def _split_frontmatter(markdown: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n?', markdown, re.DOTALL)
    if not match:
        return {}, markdown
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, markdown[match.end():]


def _parse_checkboxes(body: str) -> Tuple[List[Dict[str, Any]], str]:
    """Extract GitHub-style checkboxes from markdown body."""
    items = []
    for line in body.splitlines():
        m = re.match(r'^\s*-\s+\[([ xX])\]\s+(.*)$', line)
        if m:
            text = m.group(2).strip()
            if not text:
                continue
            items.append({
                'text': text,
                'checked': m.group(1).lower() == 'x',
            })
    if not items:
        return [], body
    remaining = CHECKBOX_RE.sub('', body)
    remaining = re.sub(r'\n{3,}', '\n\n', remaining).strip()
    return items, remaining


def _markdown_body_to_text(body: str, width: int = 48) -> str:
    from printime.styled import format_markdown_for_print
    return format_markdown_for_print(body, width)


def _resolve_template(
    meta: Dict[str, Any],
    context: Dict[str, Any],
    segments: List[Dict[str, Any]],
) -> str:
    if meta.get('template'):
        return meta['template']
    has_mermaid = any(seg.get('type') == 'mermaid' for seg in segments)
    has_items = any(seg.get('type') == 'items' for seg in segments)
    has_body = any(seg.get('type') == 'styled' for seg in segments)
    has_qr = any(seg.get('type') == 'qr' for seg in segments)
    has_ascii = any(seg.get('type') == 'ascii_art' for seg in segments)
    if has_ascii:
        return 'document'
    if (has_mermaid or has_qr) and (has_items or has_body):
        return 'document'
    if has_mermaid:
        return 'diagram'
    if has_items:
        return 'checklist'
    return 'note'


def _sync_legacy_context_fields(context: Dict[str, Any], segments: List[Dict[str, Any]], width: int) -> None:
    """Keep older template/tests fields populated from ordered segments."""
    from printime.styled import lines_to_plain_preview

    styled_lines = []
    all_items = []
    for seg in segments:
        if seg['type'] == 'styled':
            styled_lines.extend(seg['lines'])
        elif seg['type'] == 'items':
            all_items.extend(seg['items'])
        elif seg['type'] == 'mermaid' and 'mermaid' not in context:
            context['mermaid'] = seg['source']
        elif seg['type'] == 'qr' and 'qr' not in context:
            context['qr'] = seg['data']

    if all_items:
        context['items'] = all_items
    if styled_lines:
        context['content_lines'] = styled_lines
        context['content'] = lines_to_plain_preview(styled_lines, width)


def markdown_to_context(
    markdown: str,
    filename: str = "",
    width: int = 48,
    *,
    link_qr: bool = True,
    link_qr_size: int = 4,
    link_qr_align: str = 'left',
    main_url: str | None = None,
) -> Dict[str, Any]:
    """Convert markdown with YAML frontmatter to template context."""
    meta, body = _split_frontmatter(markdown)
    context: Dict[str, Any] = dict(meta)

    title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    if title_match and 'title' not in context:
        context['title'] = title_match.group(1).strip()
        body = re.sub(r'^#\s+.*$', '', body, count=1, flags=re.MULTILINE).strip()
    elif 'title' not in context:
        context['title'] = os.path.splitext(os.path.basename(filename))[0]

    from printime.services.markdown_blocks import build_print_segments

    segments = build_print_segments(
        body,
        width,
        link_qr=link_qr,
        link_qr_size=link_qr_size,
        link_qr_align=link_qr_align,
        main_url=main_url,
    )
    context['segments'] = segments
    _sync_legacy_context_fields(context, segments, width)

    template = _resolve_template(meta, context, segments)

    if template == 'jira' and 'summary' not in context and 'title' in context:
        context['summary'] = context['title']

    if template == 'email':
        if 'sender' not in context and context.get('from'):
            context['sender'] = context['from']
        if 'subject' not in context and context.get('title'):
            context['subject'] = context['title']
        if body.strip() and 'body' not in context and 'content' not in context:
            from printime.styled import markdown_to_print_lines, lines_to_plain_preview
            context['body_lines'] = markdown_to_print_lines(body, width)
            context['body'] = lines_to_plain_preview(context['body_lines'], width)

    if template in ('checklist', 'document') and context.get('items'):
        if not any(seg.get('type') == 'styled' for seg in segments) and body.strip():
            from printime.styled import markdown_to_print_lines, lines_to_plain_preview
            context['content_lines'] = markdown_to_print_lines(body, width)
            context['content'] = lines_to_plain_preview(context['content_lines'], width)
    elif template == 'diagram':
        if body.strip() and 'caption' not in context:
            from printime.styled import markdown_to_print_lines, lines_to_plain_preview
            context['caption_lines'] = markdown_to_print_lines(body, width)
            context['caption'] = lines_to_plain_preview(context['caption_lines'], width)
    elif template in ('task', 'jira', 'message', 'heading', 'receipt'):
        if body.strip() and 'content' not in context and 'description' not in context:
            from printime.styled import markdown_to_print_lines, lines_to_plain_preview
            field = 'description' if template in ('task', 'jira') else 'content'
            context[f'{field}_lines'] = markdown_to_print_lines(body, width)
            context[field] = lines_to_plain_preview(context[f'{field}_lines'], width)
    else:
        if template != 'email' and body.strip():
            from printime.styled import markdown_to_print_lines, lines_to_plain_preview
            context['content_lines'] = markdown_to_print_lines(body, width)
            context['content'] = lines_to_plain_preview(context['content_lines'], width)

    context['template'] = template
    return context


def latex_to_png(latex: str, size: str = 'medium', output_dir: Optional[str] = None) -> Optional[str]:
    if not check_latex_tools():
        print("Warning: LaTeX tools not installed (pdflatex, pdftoppm)")
        return None

    sizes = {
        'small': {'font_size': 16, 'scale': '200'},
        'medium': {'font_size': 24, 'scale': '300'},
        'large': {'font_size': 36, 'scale': '400'},
    }
    size_config = sizes.get(size, sizes['medium'])

    latex_doc = rf"""\documentclass[12pt]{{article}}
\usepackage[paperwidth=6in, paperheight=2in, margin=0.1in]{{geometry}}
\usepackage{{amsmath}}
\usepackage{{amssymb}}
\thispagestyle{{empty}}
\begin{{document}}
\fontsize{{{size_config['font_size']}}}{{{size_config['font_size'] * 1.2}}}\selectfont
\[
{latex}
\]
\end{{document}}
"""

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    base_name = 'printime_eq'
    tex_path = os.path.join(output_dir, f'{base_name}.tex')
    with open(tex_path, 'w') as f:
        f.write(latex_doc)

    try:
        result = subprocess.run(
            ['pdflatex', '-interaction=batchmode', '-output-directory', output_dir, tex_path],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
    except subprocess.TimeoutExpired:
        return None

    pdf_path = os.path.join(output_dir, f'{base_name}.pdf')
    png_path = os.path.join(output_dir, f'{base_name}-1.png')
    subprocess.run(
        ['pdftoppm', '-png', '-r', size_config['scale'], pdf_path, os.path.join(output_dir, base_name)],
        capture_output=True,
    )
    if os.path.exists(png_path):
        return png_path
    for f in os.listdir(output_dir):
        if f.startswith(base_name) and f.endswith('.png'):
            return os.path.join(output_dir, f)
    return None


def transform_file(input_path: str, output_type: Optional[str] = None) -> Dict[str, Any]:
    ext = os.path.splitext(input_path)[1].lower()

    if output_type is None:
        if ext == '.md':
            output_type = 'context'
        elif ext in ('.tex', '.latex'):
            output_type = 'image'
        else:
            output_type = 'text'

    if output_type == 'context' or ext == '.md':
        with open(input_path, 'r') as f:
            content = f.read()
        return {'type': 'context', 'content': markdown_to_context(content, input_path)}

    if output_type == 'image' or ext in ('.tex', '.latex'):
        with open(input_path, 'r') as f:
            latex = f.read()
        png_path = latex_to_png(latex)
        if png_path:
            return {'type': 'image', 'image_path': png_path}
        return {'type': 'error', 'error': 'LaTeX conversion failed'}

    with open(input_path, 'r') as f:
        content = f.read()
    return {'type': 'text', 'content': content}
