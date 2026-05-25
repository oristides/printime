#!/usr/bin/env python3
"""Fetch web pages and extract article text for printing."""

from __future__ import annotations

import html as html_module
import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SKIP_TAGS = frozenset({
    'script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'iframe', 'button',
})
BLOCK_END_TAGS = frozenset({
    'p', 'div', 'li', 'blockquote', 'pre', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
})
DEFAULT_MAX_CHARS = 12000
USER_AGENT = 'Mozilla/5.0 (compatible; Printime/0.1; +https://github.com/printime)'


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == 'br':
            self._parts.append('\n')
        elif tag.startswith('h') and len(tag) == 2 and tag[1].isdigit():
            self._parts.append('\n\n')

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in BLOCK_END_TAGS:
            self._parts.append('\n')

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        text = ''.join(self._parts)
        text = html_module.unescape(text)
        text = re.sub(r'[ \t\f\v]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def fetch_html(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or 'utf-8'
    return raw.decode(charset, errors='replace')


def _decode_embedded_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def _is_twitter_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix('www.')
    return host in {'twitter.com', 'x.com', 'mobile.twitter.com'}


def _extract_twitter(html: str) -> Tuple[str, str]:
    texts = re.findall(r'"full_text"\s*:\s*"((?:\\.|[^"\\])*)"', html)
    if not texts:
        return '', ''
    body = '\n\n'.join(_decode_embedded_json_string(text) for text in texts[:5])
    authors = re.findall(r'"screen_name"\s*:\s*"([^"]+)"', html)
    title = f'@{authors[0]}' if authors else 'Tweet'
    return title, body


def _extract_title(html: str) -> str:
    for pattern in (
        r'property="og:title"\s+content="([^"]+)"',
        r'content="([^"]+)"\s+property="og:title"',
        r'<meta\s+name="twitter:title"\s+content="([^"]+)"',
        r'<h1[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>',
    ):
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r'<[^>]+>', '', match.group(1))
            title = html_module.unescape(title).strip()
            if title and title.lower() not in ('substack', 'prof g media', 'x', 'twitter'):
                return title
    return ''


def _extract_article_html(html: str) -> str:
    patterns = (
        # Substack
        r'class="available-content"[^>]*>(.*?)(?:<div class="visibility-check"|$)',
        r'class="body markup"[^>]*>(.*?)(?:</div>\s*</div>\s*<div class="visibility-check"|$)',
        # News sites (Folha, Google Blog, etc.)
        r'itemprop="articleBody"[^>]*>(.*?)(?:</div>\s*<div|$)',
        r'class="c-news__body[^"]*"[^>]*>(.*?)(?:</div>\s*<div|$)',
        # Generic article containers
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
        r'<body[^>]*>(.*?)</body>',
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            chunk = match.group(1)
            if len(chunk.strip()) > 200:
                return chunk
    return html


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


def article_html_to_text(html: str) -> str:
    """Extract article text, preserving hyperlinks as markdown."""
    from printime.services.link_qr import normalize_document_links

    return html_to_text(normalize_document_links(html))


def _is_keep_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix('www.')
    return host == 'keep.google.com'


def url_to_context(
    url: str,
    width: int = 48,
    max_chars: Optional[int] = DEFAULT_MAX_CHARS,
    *,
    link_qr: bool = True,
    link_qr_size: int = 4,
    link_qr_align: str = 'left',
) -> Dict[str, Any]:
    """Fetch a URL and build a note template context."""
    from printime.services.transform import _markdown_body_to_text

    if _is_keep_url(url):
        raise ValueError(
            'Google Keep URLs require authentication. Use:\n'
            f'  printime keep print "{url}" --preview\n'
            'See docs/KEEP.md for setup.'
        )

    html = fetch_html(url)

    if _is_twitter_url(url):
        title, body = _extract_twitter(html)
        if not title:
            title = _extract_title(html) or 'Tweet'
    else:
        title = _extract_title(html) or urlparse(url).path.rstrip('/').split('/')[-1] or 'Article'
        article_html = _extract_article_html(html)
        body = article_html_to_text(article_html) if link_qr else html_to_text(article_html)

    if not body.strip():
        raise ValueError(f'Could not extract readable text from {url}')

    truncated = False
    if max_chars is not None and len(body) > max_chars:
        cut = body[:max_chars].rsplit('\n', 1)[0]
        body = f'{cut}\n\n[… truncated — use --max-chars 0 for full text]'
        truncated = True

    if link_qr:
        from printime.services.markdown_blocks import build_print_segments
        segments = build_print_segments(
            body,
            width,
            link_qr=True,
            link_qr_size=link_qr_size,
            link_qr_align=link_qr_align,
            main_url=url,
        )
        return {
            'title': title,
            'template': 'document',
            'source_url': url,
            'truncated': truncated,
            'segments': segments,
        }

    content = _markdown_body_to_text(body, width)
    if len(url) <= width + 10:
        content = f'{content}\n\nSource: {url}'
    else:
        content = f'{content}\n\nSource:\n{url}'

    return {
        'title': title,
        'content': content,
        'template': 'note',
        'source_url': url,
        'truncated': truncated,
    }
