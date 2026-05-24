#!/usr/bin/env python3
"""Render diagrams and prepare raster images for thermal printing."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

MERMAID_FENCE_RE = re.compile(
    r'```\s*mermaid\s*\r?\n(.*?)```',
    re.DOTALL | re.IGNORECASE,
)

# Balanced for 80mm thermal — readable size, normal weight (not heavy bold).
THERMAL_MERMAID_SCALE = 1
THERMAL_MERMAID_FONT = '16px'
THERMAL_MERMAID_BORDER = '2px'
THERMAL_LINE_DILATE = 0
THERMAL_MAX_WIDTH_RATIO = 0.92
THERMAL_UPSCALE_MAX = 1.35

PUPPETEER_SANDBOX_ARGS = ['--no-sandbox', '--disable-setuid-sandbox']

MERMAID_THERMAL_CSS = """
.mermaid svg { max-width: 100% !important; }
.nodeLabel, .label, .edgeLabel, .label text, span {
  font-weight: 500 !important;
  font-size: 16px !important;
  fill: #000 !important;
  color: #000 !important;
}
.node rect, .node circle, .node polygon, .node path {
  stroke-width: 2px !important;
  stroke: #000 !important;
}
.flowchart-link, .edgePaths path, .messageLine0, .messageLine1 {
  stroke-width: 2px !important;
  stroke: #000 !important;
}
marker path { fill: #000 !important; stroke: #000 !important; }
"""


def check_mermaid_cli() -> bool:
    if shutil.which('mmdc'):
        return True
    if shutil.which('npx'):
        return True
    return False


def _write_puppeteer_config(output_dir: str) -> str:
    path = os.path.join(output_dir, 'printime_puppeteer.json')
    with open(path, 'w') as f:
        json.dump({'args': PUPPETEER_SANDBOX_ARGS}, f)
    return path


def _write_mermaid_config(output_dir: str) -> str:
    config = {
        'theme': 'base',
        'themeVariables': {
            'darkMode': False,
            'background': '#ffffff',
            'primaryColor': '#ffffff',
            'primaryTextColor': '#000000',
            'primaryBorderColor': '#000000',
            'secondaryColor': '#ffffff',
            'tertiaryColor': '#ffffff',
            'lineColor': '#000000',
            'textColor': '#000000',
            'fontSize': THERMAL_MERMAID_FONT,
            'fontFamily': 'arial, helvetica, sans-serif',
            'primaryBorderWidth': THERMAL_MERMAID_BORDER,
            'secondaryBorderWidth': '2px',
            'tertiaryBorderWidth': '2px',
        },
        'flowchart': {
            'htmlLabels': True,
            'curve': 'linear',
            'padding': 12,
            'nodeSpacing': 50,
            'rankSpacing': 55,
            'useMaxWidth': True,
        },
        'sequence': {
            'useMaxWidth': True,
            'wrap': True,
        },
        'gantt': {
            'useMaxWidth': True,
        },
    }
    path = os.path.join(output_dir, 'printime_mermaid.json')
    with open(path, 'w') as f:
        json.dump(config, f)
    return path


def _write_mermaid_css(output_dir: str) -> str:
    path = os.path.join(output_dir, 'printime_mermaid.css')
    with open(path, 'w') as f:
        f.write(MERMAID_THERMAL_CSS.strip())
    return path


def _mermaid_command(
    input_path: str,
    output_path: str,
    width: int,
    puppeteer_config: str,
    mermaid_config: str,
    css_path: str,
    scale: int = THERMAL_MERMAID_SCALE,
) -> List[str]:
    flags = [
        '-i', input_path,
        '-o', output_path,
        '-w', str(width),
        '-s', str(scale),
        '-b', 'white',
        '-p', puppeteer_config,
        '-c', mermaid_config,
        '-C', css_path,
    ]
    if shutil.which('mmdc'):
        return ['mmdc', *flags]
    return ['npx', '-y', '@mermaid-js/mermaid-cli', *flags]


def extract_mermaid_from_markdown(body: str) -> Tuple[List[str], str]:
    """Return mermaid sources found in fenced blocks and body with them removed."""
    blocks = [m.group(1).strip() for m in MERMAID_FENCE_RE.finditer(body) if m.group(1).strip()]
    remaining = MERMAID_FENCE_RE.sub('', body)
    remaining = re.sub(r'\n{3,}', '\n\n', remaining).strip()
    return blocks, remaining


def _trim_white_borders(img, threshold: int = 248):
    from PIL import ImageOps

    gray = img.convert('L')
    mask = gray.point(lambda p: 255 if p < threshold else 0)
    bbox = mask.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def prepare_diagram_for_print(path: str, max_width: int = 576) -> str:
    """Trim margins, fit to paper, light contrast boost for thermal."""
    from PIL import Image, ImageFilter, ImageOps

    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    target_max = max(1, int(max_width * THERMAL_MAX_WIDTH_RATIO))

    with Image.open(path) as opened:
        img = opened.convert('RGB')
        img = _trim_white_borders(img)

        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize(
                (max_width, max(1, int(img.height * ratio))),
                Image.LANCZOS,
            )
        elif img.width < target_max * 0.5:
            new_w = min(target_max, max(1, int(img.width * THERMAL_UPSCALE_MAX)))
            ratio = new_w / img.width
            img = img.resize(
                (new_w, max(1, int(img.height * ratio))),
                Image.LANCZOS,
            )

        gray = ImageOps.autocontrast(img.convert('L'))
        bw = gray.point(lambda p: 0 if p < 228 else 255, mode='1')

        if THERMAL_LINE_DILATE > 1:
            inv = ImageOps.invert(bw.convert('L'))
            inv = inv.filter(ImageFilter.MaxFilter(THERMAL_LINE_DILATE))
            bw = ImageOps.invert(inv).convert('1')

        out_path = os.path.join(
            tempfile.gettempdir(),
            f'printime_diagram_{os.getpid()}_{os.path.basename(path)}',
        )
        bw.save(out_path, 'PNG')
        return out_path


def prepare_image_for_print(path: str, max_width: int = 576) -> str:
    """Scale a photo/screenshot to fit thermal paper width."""
    from PIL import Image

    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    with Image.open(path) as img:
        if img.width <= max_width:
            return path
        ratio = max_width / img.width
        resized = img.convert('RGB').resize(
            (max_width, max(1, int(img.height * ratio))),
            Image.LANCZOS,
        )
        out_path = os.path.join(
            tempfile.gettempdir(),
            f'printime_img_{os.getpid()}_{os.path.basename(path)}',
        )
        resized.save(out_path, 'PNG')
        return out_path


def mermaid_to_png(
    source: str,
    *,
    output_dir: Optional[str] = None,
    width: int = 576,
) -> Optional[str]:
    """Render mermaid diagram text or a .mmd file path to PNG."""
    if not check_mermaid_cli():
        print('Warning: mermaid-cli not found. Install: npm install -g @mermaid-js/mermaid-cli', file=sys.stderr)
        return None

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    if os.path.isfile(source):
        with open(source, 'r') as f:
            mermaid_text = f.read()
        base_name = os.path.splitext(os.path.basename(source))[0]
    else:
        mermaid_text = source
        base_name = 'printime_mermaid'

    mmd_path = os.path.join(output_dir, f'{base_name}.mmd')
    png_path = os.path.join(output_dir, f'{base_name}.png')
    render_width = max(320, int(width * THERMAL_MAX_WIDTH_RATIO))

    with open(mmd_path, 'w') as f:
        f.write(mermaid_text)

    puppeteer_config = _write_puppeteer_config(output_dir)
    mermaid_config = _write_mermaid_config(output_dir)
    css_path = _write_mermaid_css(output_dir)
    try:
        result = subprocess.run(
            _mermaid_command(
                mmd_path, png_path, render_width,
                puppeteer_config, mermaid_config, css_path,
            ),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip()
            if err:
                print(f'Warning: mermaid render failed: {err}', file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print('Warning: mermaid render timed out', file=sys.stderr)
        return None

    if os.path.exists(png_path):
        return prepare_diagram_for_print(png_path, max_width=width)
    return None
