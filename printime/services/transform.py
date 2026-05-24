#!/usr/bin/env python3
"""
Transform Service - Convert markdown and other files to print template context.
"""

import os
import re
import subprocess
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
            items.append({
                'text': m.group(2).strip(),
                'checked': m.group(1).lower() == 'x',
            })
    if not items:
        return [], body
    remaining = CHECKBOX_RE.sub('', body)
    remaining = re.sub(r'\n{3,}', '\n\n', remaining).strip()
    return items, remaining


def _markdown_body_to_text(body: str, width: int = 48) -> str:
    """Convert markdown body to plain wrapped text for note-style templates."""
    content = body.strip()
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content, flags=re.DOTALL)
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', content, flags=re.DOTALL)
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', content)
    content = re.sub(r'```[\s\S]*?```', '', content)
    content = re.sub(r'`(.+?)`', r'\1', content)
    content = re.sub(r'^\s*[-*+]\s+', '* ', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*\d+\.\s+', '* ', content, flags=re.MULTILINE)
    content = re.sub(r'^>\s*', '> ', content, flags=re.MULTILINE)

    wrapped_lines = []
    for line in content.split('\n'):
        if not line.strip():
            wrapped_lines.append('')
        elif line.strip().startswith('* '):
            wrapped_lines.append(
                textwrap.fill(line.strip(), width=width, subsequent_indent='  ')
            )
        else:
            wrapped_lines.append(textwrap.fill(line.strip(), width=width))
    return '\n'.join(wrapped_lines).strip()


def markdown_to_context(markdown: str, filename: str = "", width: int = 48) -> Dict[str, Any]:
    """Convert markdown with YAML frontmatter to template context."""
    meta, body = _split_frontmatter(markdown)
    context: Dict[str, Any] = dict(meta)

    title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    if title_match and 'title' not in context:
        context['title'] = title_match.group(1).strip()
        body = re.sub(r'^#\s+.*$', '', body, count=1, flags=re.MULTILINE).strip()
    elif 'title' not in context:
        context['title'] = os.path.splitext(os.path.basename(filename))[0]

    items, body = _parse_checkboxes(body)
    if items:
        context['items'] = items
        if 'template' not in context:
            context['template'] = 'checklist'

    template = context.get('template', 'note')

    if template == 'jira' and 'summary' not in context and 'title' in context:
        context['summary'] = context['title']

    if template == 'checklist' and items:
        pass  # items already set
    elif template in ('task', 'jira', 'message', 'heading', 'receipt'):
        if body.strip() and 'content' not in context and 'description' not in context:
            field = 'description' if template in ('task', 'jira') else 'content'
            context[field] = _markdown_body_to_text(body, width)
    else:
        if body.strip():
            context['content'] = _markdown_body_to_text(body, width)

    if 'template' not in context:
        context['template'] = 'note'

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
