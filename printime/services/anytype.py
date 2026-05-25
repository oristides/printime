#!/usr/bin/env python3
"""
Anytype Service - Fetch pages from Anytype and print.

Requires:
- anytype CLI installed with service running
- anytype auth login (account key — not the API key)
- ANYTYPE_API_KEY in .env

Usage:
  anytype service start
  anytype auth create printime
  anytype space join '<invite-link>'   # repeat for each space
  printime anytype list
  printime anytype fetch <object-id> --template note --preview
"""

import json
import re
import subprocess
import urllib.error
import urllib.request
from typing import Optional, List, Dict, Any, Tuple

from printime.config import get_anytype_config, load_env

DEFAULT_API_URL = "http://127.0.0.1:31012"
API_VERSION = "2025-11-08"


def get_api_key() -> Optional[str]:
    load_env()
    return get_anytype_config().get('api_key')


def get_default_space_id() -> Optional[str]:
    load_env()
    return get_anytype_config().get('space_id')


def get_api_url() -> str:
    load_env()
    import os
    return os.getenv('ANYTYPE_API_URL', DEFAULT_API_URL).rstrip('/')


def _api_request(path: str, api_key: str, method: str = 'GET', body: dict | None = None) -> Tuple[int, Any]:
    url = f"{get_api_url()}{path}"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Anytype-Version': API_VERSION,
        'Accept': 'application/json',
    }
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {'message': raw[:300]}
        return e.code, payload
    except urllib.error.URLError as e:
        return 0, {'message': str(e.reason)}


def list_spaces_via_api() -> List[Dict[str, str]]:
    """Return all spaces the bot account has joined."""
    api_key = get_api_key()
    if not api_key:
        return []

    status, payload = _api_request('/v1/spaces', api_key)
    if status != 200:
        return []

    spaces = []
    for item in payload.get('data', []):
        if not isinstance(item, dict):
            continue
        spaces.append({
            'id': item.get('id', ''),
            'name': item.get('name') or '(unnamed)',
        })
    return spaces


def join_space(invite_link: str) -> bool:
    """Join a space using an invite link from Anytype Desktop."""
    link = invite_link.strip()
    if not link:
        return False
    result = run_anytype_command(['space', 'join', link])
    if result['success']:
        print(result['output'] or f"Joined space via invite link.")
        return True
    print(f"Failed to join: {result['error']}")
    return False


def join_spaces(invite_links: List[str]) -> int:
    """Join multiple spaces. Returns count of successful joins."""
    joined = 0
    for link in invite_links:
        link = link.strip()
        if not link or link.startswith('#'):
            continue
        print(f"\nJoining: {link[:60]}{'...' if len(link) > 60 else ''}")
        if join_space(link):
            joined += 1
    print(f"\nJoined {joined} space(s).")
    list_spaces()
    return joined


def join_spaces_from_file(path: str) -> int:
    with open(path, 'r') as f:
        links = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    return join_spaces(links)


def run_anytype_command(args: List[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ['anytype'] + args,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return {'success': True, 'output': result.stdout}
        return {'success': False, 'error': result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def list_spaces() -> List[Dict[str, str]]:
    """List spaces the bot can access."""
    spaces = list_spaces_via_api()
    if spaces:
        print(f"{'SPACE ID':<74} {'NAME'}")
        print(f"{'─' * 74} {'────'}")
        for space in spaces:
            print(f"{space['id']:<74} {space['name']}")
        print(f"\n{len(spaces)} space(s) available.")
        if get_api_url().endswith('31012'):
            print("Join more with: anytype space join '<invite-link>'")
        return spaces

    result = run_anytype_command(['space', 'list'])
    if not result['success']:
        print(f"Error listing spaces: {result['error']}")
        print("Run: anytype auth login")
        return []
    print(result['output'])
    return []


def fetch_page_via_api(page_id: str, api_key: str, space_id: str) -> Optional[Dict[str, Any]]:
    status, payload = _api_request(f'/v1/spaces/{space_id}/objects/{page_id}', api_key)
    if status == 200:
        return payload
    return None


def fetch_page(page_id: str, space_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch an Anytype object, searching all joined spaces if needed."""
    load_env()
    api_key = get_api_key()
    if not api_key:
        print("Error: ANYTYPE_API_KEY not set in .env")
        return None

    spaces_to_try: List[str] = []
    if space_id:
        spaces_to_try = [space_id]
    else:
        default_space = get_default_space_id()
        if default_space:
            spaces_to_try.append(default_space)
        for space in list_spaces_via_api():
            if space['id'] not in spaces_to_try:
                spaces_to_try.append(space['id'])

    if not spaces_to_try:
        print("Error: bot account has no joined spaces.")
        print("Join one with: anytype space join '<invite-link-from-anytype-desktop>'")
        return None

    errors = []
    for sid in spaces_to_try:
        page = fetch_page_via_api(page_id, api_key, sid)
        if page:
            if len(spaces_to_try) > 1:
                name = next((s['name'] for s in list_spaces_via_api() if s['id'] == sid), sid)
                print(f"Found in space: {name} ({sid})")
            return page
        errors.append(sid)

    print(
        f"Object {page_id} not found in {len(spaces_to_try)} joined space(s).\n"
        "Check the object ID, or join the space that contains it:\n"
        "  anytype space join '<invite-link>'"
    )
    return None


def _unwrap_search_hit(item: Any) -> Optional[Dict[str, Any]]:
    """Normalize /v1/search result item to an object dict."""
    if not isinstance(item, dict):
        return None
    nested = item.get('object')
    if isinstance(nested, dict):
        return nested
    if item.get('id'):
        return item
    return None


def global_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search all Desktop spaces via /v1/search."""
    load_env()
    api_key = get_api_key()
    if not api_key:
        print("Error: ANYTYPE_API_KEY not set in .env")
        return []

    status, payload = _api_request(
        '/v1/search',
        api_key,
        method='POST',
        body={'query': query},
    )
    if status != 200:
        print(f"Search failed ({status}): {payload}")
        return []

    results = []
    for item in payload.get('data', [])[:limit]:
        obj = _unwrap_search_hit(item)
        if obj and obj.get('id'):
            results.append(obj)
    return results


def find_page_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Find a single page by title search (exact match preferred)."""
    hits = global_search(query, limit=20)
    if not hits:
        return None

    q = query.strip().lower()
    for obj in hits:
        if (obj.get('name') or '').strip().lower() == q:
            return obj

    for obj in hits:
        if q in (obj.get('name') or '').lower():
            return obj

    return hits[0]


def print_page_by_query(
    query: str,
    template: Optional[str] = None,
    preview: bool = False,
    config: Optional[Dict] = None,
    yes: bool = False,
) -> bool:
    """Search Anytype by title and print the best match."""
    obj = find_page_by_query(query)
    if not obj:
        print(f"No page found for: {query!r}")
        return False

    page_id = obj['id']
    space_id = obj.get('space_id')
    print(f"Matched: {obj.get('name')!r} ({page_id})")
    return print_page(
        page_id,
        template=template,
        space_id=space_id,
        preview=preview,
        config=config,
        yes=yes,
    )


def normalize_anytype_markdown(text: str) -> str:
    """Fix markdown quirks from Anytype export / paste."""
    from printime.styled import normalize_markdown_text

    while '\\`' in text:
        text = text.replace('\\`', '`')
    text = re.sub(r'^(\s*)-\[([ xX])\]', r'\1- [\2]', text, flags=re.MULTILINE)
    return normalize_markdown_text(text)


def _page_markdown_source(obj: Dict[str, Any]) -> str:
    """Combine Anytype markdown/body fields (API may split prose and checklists)."""
    markdown = (obj.get('markdown') or '').strip()
    body = (obj.get('body') or '').strip()
    if markdown and body and markdown != body:
        if markdown in body:
            combined = body
        elif body in markdown:
            combined = markdown
        else:
            combined = f'{body}\n\n{markdown}'
    else:
        combined = markdown or body or (obj.get('snippet') or '')
    return normalize_anytype_markdown(combined)


def page_to_template_context(
    page: Dict[str, Any],
    width: int = 48,
    *,
    link_qr: bool = True,
    link_qr_size: int = 4,
    link_qr_align: str = 'left',
) -> Dict[str, Any]:
    """Convert Anytype API response to printime template context."""
    obj = page.get('object', page)

    name = obj.get('name') or obj.get('title') or 'Untitled'
    markdown = _page_markdown_source(obj)

    if markdown:
        from printime.services.transform import _split_frontmatter, markdown_to_context

        meta, _ = _split_frontmatter(markdown)
        context = markdown_to_context(
            markdown,
            name,
            width,
            link_qr=link_qr,
            link_qr_size=link_qr_size,
            link_qr_align=link_qr_align,
        )
        if not meta.get('title'):
            context['title'] = name
    else:
        context = {'title': name, 'content': obj.get('snippet', '')}

    type_info = obj.get('type') or {}
    type_key = (type_info.get('key') or type_info.get('name') or '').lower()
    if type_key in ('task', 'todo'):
        context.setdefault('template', 'task')
    elif type_key in ('checklist',):
        context.setdefault('template', 'checklist')
    elif 'template' not in context:
        context['template'] = 'note'

    for prop in obj.get('properties', []):
        key = prop.get('key')
        if not key:
            continue
        if 'text' in prop and key not in context:
            context[key] = prop['text']
        elif 'select' in prop and key not in context:
            tag = prop['select']
            context[key] = tag.get('name') or tag.get('key') if isinstance(tag, dict) else tag
        elif 'checkbox' in prop and key == 'done':
            context['completed'] = prop['checkbox']

    if type_key == 'task' and 'description' not in context and 'content' in context:
        context['description'] = context.pop('content')

    return context


def detect_template(page: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Pick a printime template from Anytype object type and parsed context."""
    if context.get('template'):
        return context['template']

    obj = page.get('object', page)
    type_key = ((obj.get('type') or {}).get('key') or '').lower()
    name = (obj.get('name') or '').lower()

    if 'jira' in name or 'ticket' in name:
        return 'jira'
    if type_key in ('task', 'todo') or 'task' in name:
        return 'task'
    if 'receipt' in name:
        return 'receipt'

    return 'note'


def print_page(page_id: str, template: Optional[str] = None, space_id: Optional[str] = None,
               preview: bool = False, config: Optional[Dict] = None, yes: bool = False):
    """Fetch an Anytype page and print it."""
    from printime.cli import _print_template, create_printer, load_config

    print(f"Fetching page: {page_id}")

    page = fetch_page(page_id, space_id=space_id)
    if not page:
        return False

    if config is None:
        config = load_config()

    width = config['printer']['width']
    from printime.services.link_qr import link_qr_kwargs_from_config

    lq = link_qr_kwargs_from_config(config)
    context = page_to_template_context(page, width, **lq)
    template = template or detect_template(page, context)

    print(f"Using template: {template}")

    printer = create_printer(config)
    _print_template(
        printer,
        config,
        template,
        context,
        preview=preview,
        yes=yes,
        label='Anytype',
    )
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Anytype integration')
    parser.add_argument('command', choices=['list', 'fetch'])
    parser.add_argument('page_id', nargs='?', help='Object ID')
    parser.add_argument('--space', '-s', help='Space ID (optional — searches all joined spaces by default)')
    parser.add_argument('--template', '-t', help='Template to use')
    parser.add_argument('--preview', '-p', action='store_true', help='Preview only; no paper unless --yes')

    args = parser.parse_args()

    if args.command == 'list':
        list_spaces()
    elif args.command == 'fetch':
        if not args.page_id:
            print("Error: page_id required")
            return 1
        print_page(args.page_id, args.template, space_id=args.space, preview=args.preview)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
