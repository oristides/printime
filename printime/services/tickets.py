#!/usr/bin/env python3
"""Extract QR codes and barcodes from ticket PDFs for thermal printing."""

from __future__ import annotations

import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from pyzbar.pyzbar import decode as zbar_decode
    from pyzbar.pyzbar import ZBarSymbol
    HAS_ZBAR = True
except Exception:
    HAS_ZBAR = False
    zbar_decode = None
    ZBarSymbol = None

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass(order=True)
class DetectedCode:
    sort_index: Tuple[int, float, float] = field(compare=True)
    page: int = 0
    kind: str = 'qrcode'  # qrcode | barcode | code_image
    symbology: str = ''
    data: str = ''
    image_path: str = ''
    width: int = 0
    height: int = 0
    digest: str = ''


def _require_pdf_deps() -> None:
    if not HAS_PYMUPDF:
        raise ImportError(
            'Ticket PDF support requires pymupdf and related packages.\n'
            '  pipx inject printime pymupdf pyzbar "markitdown[pdf]" opencv-python-headless\n'
            '  — or reinstall from repo:\n'
            '  pipx install -e '
            '~/Documents/repos/random_projects/printime[all] --force'
        )
    if not HAS_PIL:
        raise ImportError('Ticket PDF support requires pillow')


def _pil_to_bgr(pil: Image.Image):
    import numpy as np
    arr = np.array(pil.convert('RGB'))
    return arr[:, :, ::-1].copy()


def _decode_pil(pil: Image.Image) -> List[Tuple[str, str]]:
    """Return list of (symbology, data) from an image."""
    found: List[Tuple[str, str]] = []
    if HAS_ZBAR and zbar_decode is not None:
        for sym in zbar_decode(pil, symbols=[ZBarSymbol.QRCODE, ZBarSymbol.CODE128,
                                               ZBarSymbol.EAN13, ZBarSymbol.PDF417,
                                               ZBarSymbol.I25, ZBarSymbol.CODE39]):
            kind = sym.type.lower()
            data = sym.data.decode('utf-8', errors='replace').strip()
            if data:
                found.append((kind, data))

    if HAS_CV2 and not found:
        det = cv2.QRCodeDetector()
        data, _, _ = det.detectAndDecode(_pil_to_bgr(pil))
        if data:
            found.append(('qrcode', data.strip()))
        ok, decoded, _, _ = det.detectAndDecodeMulti(_pil_to_bgr(pil))
        if ok and decoded is not None:
            for item in decoded:
                if item and ('qrcode', item.strip()) not in found:
                    found.append(('qrcode', item.strip()))
    return found


def _is_code_image(w: int, h: int) -> bool:
    if w < 80 and h < 80:
        return False
    if w >= 80 and h >= 80 and 0.65 <= w / max(h, 1) <= 1.5:
        return True
    if w >= 160 and h >= 40 and w / max(h, 1) >= 1.6:
        return True
    return False


def _save_temp_png(pil: Image.Image, prefix: str = 'printime_code') -> str:
    fd, path = tempfile.mkstemp(prefix=prefix, suffix='.png')
    os.close(fd)
    pil.save(path)
    return path


def _normalize_kind(symbology: str) -> str:
    sym = symbology.lower()
    if sym in ('qrcode', 'qr'):
        return 'qrcode'
    return 'barcode'


def _filter_redundant_images(codes: List[DetectedCode]) -> List[DetectedCode]:
    """Drop square QR raster images when we already have decoded QR data."""
    has_qr = any(c.kind == 'qrcode' and c.data for c in codes)
    out: List[DetectedCode] = []
    for code in codes:
        if code.kind == 'code_image' and has_qr:
            if code.width == code.height and code.width <= 180:
                continue
        out.append(code)
    return out


def _dedupe_codes(codes: List[DetectedCode]) -> List[DetectedCode]:
    seen_data: set[Tuple[int, str, str]] = set()
    seen_digest: set[Tuple[int, str]] = set()
    out: List[DetectedCode] = []
    for code in sorted(codes):
        if code.data:
            key = (code.page, code.kind, code.data)
            if key in seen_data:
                continue
            seen_data.add(key)
        elif code.digest:
            key = (code.page, code.digest)
            if key in seen_digest:
                continue
            seen_digest.add(key)
        out.append(code)
    return _filter_redundant_images(out)


def extract_codes_from_pdf(pdf_path: str) -> List[DetectedCode]:
    """Detect all QR/barcodes in document order (page, top-to-bottom, left-to-right)."""
    _require_pdf_deps()
    doc = fitz.open(pdf_path)
    codes: List[DetectedCode] = []

    try:
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            page_codes: List[DetectedCode] = []

            for info in page.get_image_info(xrefs=True):
                xref = int(info.get('xref') or 0)
                w = int(info.get('width') or 0)
                h = int(info.get('height') or 0)
                if not _is_code_image(w, h):
                    continue
                bbox = info.get('bbox') or (0, 0, 0, 0)
                y0, x0 = float(bbox[1]), float(bbox[0])
                digest = ''
                pil = None
                if xref:
                    try:
                        raw = doc.extract_image(xref)
                        digest = raw.get('digest', b'').hex() if raw.get('digest') else ''
                        pil = Image.open(io.BytesIO(raw['image']))
                    except Exception:
                        pil = None

                if pil is None:
                    continue

                decoded = _decode_pil(pil)
                if decoded:
                    for sym, data in decoded:
                        page_codes.append(DetectedCode(
                            sort_index=(page_idx, y0, x0),
                            page=page_idx,
                            kind=_normalize_kind(sym),
                            symbology=sym,
                            data=data,
                            width=w,
                            height=h,
                            digest=digest,
                        ))
                else:
                    page_codes.append(DetectedCode(
                        sort_index=(page_idx, y0, x0),
                        page=page_idx,
                        kind='code_image',
                        symbology='image',
                        data='',
                        image_path=_save_temp_png(pil),
                        width=w,
                        height=h,
                        digest=digest,
                    ))

            # Full-page pass catches codes not tied to a single xref (e.g. vector overlays).
            if HAS_CV2:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
                det = cv2.QRCodeDetector()
                ok, decoded, points, _ = det.detectAndDecodeMulti(arr)
                if ok and decoded is not None and points is not None:
                    for i, data in enumerate(decoded):
                        if not data:
                            continue
                        pt = points[i][0]
                        y0, x0 = float(pt[1]), float(pt[0])
                        if any(c.data == data.strip() and c.page == page_idx for c in page_codes):
                            continue
                        page_codes.append(DetectedCode(
                            sort_index=(page_idx, y0, x0),
                            page=page_idx,
                            kind='qrcode',
                            symbology='qrcode',
                            data=data.strip(),
                            width=0,
                            height=0,
                        ))

            codes.extend(page_codes)
    finally:
        doc.close()

    return _dedupe_codes(codes)


def extract_pdf_text(pdf_path: str) -> str:
    """Optional text/metadata via markitdown, falling back to pymupdf."""
    try:
        from markitdown import MarkItDown
        result = MarkItDown().convert(pdf_path)
        return (result.text_content or '').strip()
    except Exception:
        pass
    if not HAS_PYMUPDF:
        return ''
    doc = fitz.open(pdf_path)
    try:
        parts = [doc[i].get_text().strip() for i in range(doc.page_count)]
        return '\n\n'.join(p for p in parts if p)
    finally:
        doc.close()


def _pick_title(text: str, pdf_path: str) -> str:
    for pat in (
        r'(?m)^EVENTO\s*\n(.+)$',
        r'(?m)^Event:\s*(.+)$',
        r'(?m)^([^\n]+Innovation Week[^\n]*)',
        r'(?m)^([A-Z0-9][A-Z0-9 \-]{4,})$',
    ):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()[:48]
    return os.path.splitext(os.path.basename(pdf_path))[0]


def _pick_caption(text: str) -> str:
    lines = []
    for label, pat in (
        ('date', r'(?m)^DATA DO EVENTO\s*\n(.+)$'),
        ('venue', r'(?m)^LOCAL\s*\n(.+)$'),
        ('seat', r'(?m)^ASSENTO\s*\n(.+)$'),
    ):
        m = re.search(pat, text)
        if m:
            lines.append(m.group(1).strip())
    return ' · '.join(lines[:3])


def codes_to_segments(codes: List[DetectedCode], *, qr_size: int = 10) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    for code in codes:
        if code.kind == 'qrcode' and code.data:
            segments.append({
                'type': 'qr',
                'data': code.data,
                'qr_size': qr_size,
                'center': True,
                'ticket_code': True,
            })
        elif code.kind == 'barcode' and code.data:
            segments.append({
                'type': 'barcode',
                'data': code.data,
                'symbology': code.symbology or 'barcode',
                'center': True,
                'ticket_code': True,
            })
        elif code.image_path:
            segments.append({
                'type': 'code_image',
                'image_path': code.image_path,
                'symbology': code.symbology or 'image',
                'center': True,
                'ticket_code': True,
            })
    return segments


def pdf_to_ticket_context(pdf_path: str, width: int = 48) -> Dict[str, Any]:
    """Build printime context for ticket PDF printing."""
    from printime.styled import lines_to_plain_preview, markdown_to_print_lines

    codes = extract_codes_from_pdf(pdf_path)
    text = extract_pdf_text(pdf_path)
    title = _pick_title(text, pdf_path)
    caption = _pick_caption(text)

    segments: List[Dict[str, Any]] = []
    segments.extend(codes_to_segments(codes))

    return {
        'template': 'ticket',
        'title': title,
        'caption': caption or None,
        'source_pdf': pdf_path,
        'segments': segments,
        'codes': [code.__dict__ for code in codes],
    }
