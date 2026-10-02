"""Update only the Fable README block. Uses the unofficial Fable API."""
import html
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import UUID

START = '<!-- FABLE-READING:START -->'
END = '<!-- FABLE-READING:END -->'
BASE = 'https://api.fable.co'


class SyncError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError('Unexpected API redirect; README preserved.')


def api_url(url):
    url = urljoin(BASE, url)
    parts = urlsplit(url)
    if (parts.scheme, parts.netloc) != ('https', 'api.fable.co'):
        raise SyncError('Unexpected pagination host; README preserved.')
    return url


def fetch_items(url, token):
    items, seen = [], set()
    opener = build_opener(NoRedirect())
    while url:
        url = api_url(url)
        if url in seen or len(seen) >= 100:
            raise SyncError('Invalid pagination; README preserved.')
        seen.add(url)
        request = Request(url, headers={'Authorization': 'JWT ' + token,
                          'Accept': 'application/json', 'Origin': 'https://fable.co',
                          'Referer': 'https://fable.co/'})
        try:
            with opener.open(request, timeout=30) as response:
                data = json.load(response)
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise SyncError('Fable authentication failed. Replace FABLE_AUTH_TOKEN in Actions secrets.') from None
            raise SyncError(f'Fable returned HTTP {exc.code}; README preserved.') from None
        except (URLError, TimeoutError, ValueError):
            raise SyncError('Fable request failed; README preserved.') from None
        if isinstance(data, list):
            page, following = data, None
        elif isinstance(data, dict) and isinstance(data.get('results'), list):
            page, following = data['results'], data.get('next')
            if following is not None and not isinstance(following, str):
                raise SyncError('Unexpected pagination format; README preserved.')
        else:
            raise SyncError('Unexpected Fable response format; README preserved.')
        if any(not isinstance(item, dict) for item in page):
            raise SyncError('Unexpected Fable entry format; README preserved.')
        items.extend(page)
        url = following
    return items


def label(value):
    return str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')


def select_list(lists, override=''):
    if override:
        matches = [item for item in lists if str(item.get('id')) == override]
    else:
        matches = [item for item in lists if any(label(item.get(key)) in
                   {'currently reading', 'reading', 'in progress'}
                   for key in ('name', 'title', 'slug', 'type'))]
    if len(matches) != 1 or not matches[0].get('id'):
        raise SyncError('Cannot identify one Currently Reading list. Set the FABLE_READING_LIST_ID repository variable.')
    return str(matches[0]['id'])


def safe_url(value):
    if not isinstance(value, str):
        return ''
    parts = urlsplit(value)
    return value if parts.scheme == 'https' and parts.netloc and not parts.username and not parts.password else ''


def number(value):
    try:
        result = int(value)
        return result if result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def render(books):
    if not books:
        return '📖 No books currently in my Fable reading list.'
    rows, seen = [], set()
    for entry in books:
        book = entry.get('book', entry)
        if not isinstance(book, dict) or not book.get('title'):
            raise SyncError('Book metadata changed; README preserved.')
        identity = str(book.get('id') or book['title'])
        if identity in seen:
            continue
        seen.add(identity)
        title = html.escape(str(book['title']))
        authors = book.get('authors') or []
        if not isinstance(authors, list):
            authors = []
        author = html.escape(', '.join(str(a.get('name') or '') if isinstance(a, dict)
                                      else str(a) for a in authors))
        link = safe_url(book.get('url') or book.get('share_url'))
        title = f'<a href="{html.escape(link, quote=True)}">{title}</a>' if link else title
        cover = safe_url(book.get('cover_image'))
        image = f'<img src="{html.escape(cover, quote=True)}" width="80" alt="Book cover" />' if cover else '📖'
        progress = book.get('reading_progress') or entry.get('reading_progress') or {}
        if not isinstance(progress, dict):
            progress = {}
        current = number(progress.get('current_page', entry.get('current_page')))
        total = number(progress.get('page_count') or book.get('page_count') or book.get('pages'))
        detail = ''
        if current is not None and total:
            percent = min(100, round(current / total * 100))
            filled = round(percent / 10)
            detail = f'<br /><br />📖 {current} / {total} pages · {percent}%<br /><code>{"█" * filled}{"░" * (10 - filled)}</code>'
        elif current is not None:
            detail = f'<br /><br />📖 Page {current}'
        rows.append(f'<tr><td width="100">{image}</td><td><strong>{title}</strong><br />{author}{detail}</td></tr>')
        if len(rows) == 2:
            break
    return '<table>\n' + '\n'.join(rows) + '\n</table>\n\n<sub>Synced from Fable · up to two current reads</sub>'


def replace_block(text, content):
    if text.count(START) != 1 or text.count(END) != 1:
        raise SyncError('Expected exactly one Fable README block.')
    start = text.index(START) + len(START)
    end = text.index(END)
    if end < start:
        raise SyncError('Invalid Fable README markers.')
    return text[:start] + '\n' + content + '\n' + text[end:]


def main():
    user = os.getenv('FABLE_USER_ID', '').strip()
    token = os.getenv('FABLE_AUTH_TOKEN', '').strip()
    for prefix in ('JWT ', 'Bearer '):
        if token.startswith(prefix):
            token = token[len(prefix):]
    if not user or not token:
        raise SyncError('Add FABLE_USER_ID and FABLE_AUTH_TOKEN to repository Actions secrets.')
    try:
        UUID(user)
    except ValueError:
        raise SyncError('FABLE_USER_ID must be the UUID from a Fable API request.') from None
    root = f'{BASE}/api/v2/users/{quote(user, safe="")}/book_lists'
    lists = fetch_items(root, token)
    list_id = select_list(lists, os.getenv('FABLE_READING_LIST_ID', '').strip())
    books = fetch_items(root + '/' + quote(list_id, safe='') + '/books?limit=100&offset=0', token)
    content = render(books)
    path = Path('README.md')
    original = path.read_text(encoding='utf-8')
    updated = replace_block(original, content)
    if updated != original:
        path.write_text(updated, encoding='utf-8')
    print('Fable reading section updated.' if updated != original else 'Reading section unchanged.')


if __name__ == '__main__':
    try:
        main()
    except SyncError as exc:
        print(f'::error::{exc}', file=sys.stderr)
        sys.exit(1)
