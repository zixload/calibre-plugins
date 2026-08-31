#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
One adapter per free API, each turning a search into Candidate records.

Every provider takes a *fetch* callable so the module never imports calibre:
the plugin passes a browser backed fetcher, the tests pass urllib.  A provider
that fails, times out or changes shape returns an empty list and logs; it must
never take the whole search down with it.

Keyless APIs only. Google Books is deliberately absent: without an API key it
answers HTTP 429 from a shared anonymous quota.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import re
from urllib.parse import quote

from .candidates import Candidate

HTML_TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>', re.IGNORECASE)


def clean_html(text):
    if not text:
        return ''
    text = BR.sub('\n', text)
    text = HTML_TAG.sub('', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _year(value):
    match = re.search(r'(\d{4})', str(value or ''))
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------
# Manga, manhwa, manhua, light novels and web novels
# --------------------------------------------------------------------------

ANILIST_URL = 'https://graphql.anilist.co'
ANILIST_QUERY = '''
query ($search: String) {
  Page(perPage: 5) {
    media(search: $search, type: MANGA) {
      id format status
      title { romaji english native }
      startDate { year }
      genres
      description(asHtml: false)
      countryOfOrigin
      coverImage { large }
      siteUrl
      staff(perPage: 6) { edges { role node { name { full } } } }
    }
  }
}'''

WRITING_ROLES = ('story', 'author', 'original', 'art')


def anilist(fetch, title, authors=None, log=None):
    payload = json.dumps({'query': ANILIST_QUERY,
                          'variables': {'search': title}}).encode('utf-8')
    raw = fetch(ANILIST_URL, data=payload,
                headers={'Content-Type': 'application/json',
                         'Accept': 'application/json'})
    data = json.loads(raw)['data']['Page']['media']
    out = []
    for item in data:
        names = item.get('title') or {}
        staff = []
        for edge in (item.get('staff') or {}).get('edges', []):
            role = (edge.get('role') or '').lower()
            name = ((edge.get('node') or {}).get('name') or {}).get('full')
            if name and any(word in role for word in WRITING_ROLES):
                if name not in staff:
                    staff.append(name)
        language = {'JP': 'jpn', 'KR': 'kor', 'CN': 'chi', 'TW': 'chi'}.get(
            item.get('countryOfOrigin') or '')
        out.append(Candidate(
            'AniList',
            names.get('english') or names.get('romaji') or '',
            native_title=names.get('native') or '',
            authors=staff[:3],
            year=(item.get('startDate') or {}).get('year'),
            tags=list(item.get('genres') or []),
            comments=clean_html(item.get('description')),
            languages=[language] if language else [],
            identifiers={'anilist': str(item.get('id'))},
            cover_url=(item.get('coverImage') or {}).get('large') or '',
            url=item.get('siteUrl') or '',
            kind='manga'))
    return out


def mangadex(fetch, title, authors=None, log=None):
    url = ('https://api.mangadex.org/manga?title=%s&limit=5'
           '&includes[]=author&includes[]=artist' % quote(title))
    data = json.loads(fetch(url)).get('data') or []
    out = []
    for item in data:
        attrs = item.get('attributes') or {}
        titles = attrs.get('title') or {}
        alt = {}
        for entry in attrs.get('altTitles') or []:
            alt.update(entry)
        main = titles.get('en') or next(iter(titles.values()), '')
        native = ''
        for key in ('ja', 'ko', 'zh', 'zh-hk', 'ja-ro'):
            if alt.get(key):
                native = alt[key]
                break
        people = []
        for rel in item.get('relationships') or []:
            if rel.get('type') in ('author', 'artist'):
                name = (rel.get('attributes') or {}).get('name')
                if name and name not in people:
                    people.append(name)
        tags = []
        for tag in attrs.get('tags') or []:
            name = ((tag.get('attributes') or {}).get('name') or {}).get('en')
            if name:
                tags.append(name)
        descriptions = attrs.get('description') or {}
        language = {'ja': 'jpn', 'ko': 'kor', 'zh': 'chi'}.get(
            attrs.get('originalLanguage') or '')
        out.append(Candidate(
            'MangaDex', main,
            native_title=native,
            authors=people[:3],
            year=attrs.get('year'),
            tags=tags[:10],
            comments=clean_html(descriptions.get('en') or ''),
            languages=[language] if language else [],
            identifiers={'mangadex': item.get('id') or ''},
            url='https://mangadex.org/title/%s' % item.get('id', ''),
            kind='manga'))
    return out


def kitsu(fetch, title, authors=None, log=None):
    url = ('https://kitsu.io/api/edge/manga?filter%%5Btext%%5D=%s'
           '&page%%5Blimit%%5D=5' % quote(title))
    # Kitsu speaks JSON:API and answers 406 to a plain application/json Accept
    raw = fetch(url, headers={'Accept': 'application/vnd.api+json'})
    data = json.loads(raw).get('data') or []
    out = []
    for item in data:
        attrs = item.get('attributes') or {}
        titles = attrs.get('titles') or {}
        native = titles.get('ja_jp') or titles.get('ko_kr') or ''
        cover = (attrs.get('posterImage') or {}).get('large') or ''
        out.append(Candidate(
            'Kitsu',
            attrs.get('canonicalTitle') or titles.get('en') or '',
            native_title=native,
            year=_year(attrs.get('startDate')),
            comments=clean_html(attrs.get('synopsis')),
            identifiers={'kitsu': item.get('id') or ''},
            cover_url=cover,
            url='https://kitsu.io/manga/%s' % (attrs.get('slug') or ''),
            kind='manga'))
    return out


def jikan(fetch, title, authors=None, log=None):
    """MyAnimeList through Jikan. Often 504 when MAL itself is unwell."""
    url = 'https://api.jikan.moe/v4/manga?q=%s&limit=5' % quote(title)
    data = json.loads(fetch(url)).get('data') or []
    out = []
    for item in data:
        published = ((item.get('published') or {}).get('prop') or {})
        out.append(Candidate(
            'MyAnimeList',
            item.get('title_english') or item.get('title') or '',
            native_title=item.get('title_japanese') or '',
            authors=[a.get('name', '') for a in (item.get('authors') or [])][:3],
            year=(published.get('from') or {}).get('year'),
            tags=[g.get('name', '') for g in (item.get('genres') or [])][:8],
            comments=clean_html(item.get('synopsis')),
            identifiers={'mal': str(item.get('mal_id') or '')},
            cover_url=((item.get('images') or {}).get('jpg') or {}).get(
                'large_image_url') or '',
            url=item.get('url') or '',
            kind='manga'))
    return out


# --------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------

def openlibrary(fetch, title, authors=None, log=None):
    query = title
    if authors:
        query += ' ' + ' '.join(authors[:1])
    url = ('https://openlibrary.org/search.json?q=%s&limit=5&fields='
           'title,author_name,first_publish_year,publisher,subject,language,'
           'cover_i,key,isbn' % quote(query))
    docs = json.loads(fetch(url)).get('docs') or []
    out = []
    for doc in docs:
        cover = doc.get('cover_i')
        identifiers = {'openlibrary': (doc.get('key') or '').split('/')[-1]}
        isbns = doc.get('isbn') or []
        if isbns:
            identifiers['isbn'] = isbns[0]
        out.append(Candidate(
            'Open Library', doc.get('title') or '',
            authors=list(doc.get('author_name') or [])[:3],
            year=doc.get('first_publish_year'),
            publisher=(doc.get('publisher') or [''])[0],
            tags=list(doc.get('subject') or [])[:10],
            languages=list(doc.get('language') or [])[:2],
            identifiers=identifiers,
            cover_url=('https://covers.openlibrary.org/b/id/%s-L.jpg' % cover)
                      if cover else '',
            url='https://openlibrary.org%s' % (doc.get('key') or ''),
            kind='book'))
    return out


BNF_URL = ('https://catalogue.bnf.fr/api/SRU?version=1.2&operation='
           'searchRetrieve&recordSchema=dublincore&maximumRecords=5&query=%s')


def bnf(fetch, title, authors=None, log=None):
    """The French national library. Excellent on french editions."""
    query = 'bib.title all "%s"' % title.replace('"', '')
    if authors:
        query += ' and bib.author all "%s"' % authors[0].replace('"', '')
    raw = fetch(BNF_URL % quote(query))
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    out = []
    for record in re.findall(r'<srw:record\b.*?</srw:record>', raw, re.S):
        def pick(tag, several=False):
            found = re.findall(r'<dc:%s>(.*?)</dc:%s>' % (tag, tag), record, re.S)
            found = [clean_html(f).strip() for f in found if f.strip()]
            return found if several else (found[0] if found else '')
        name = pick('title')
        if not name:
            continue
        creators = pick('creator', True) or pick('contributor', True)
        creators = [re.sub(r'\s*\(\d{4}-?\d{0,4}\)\s*$', '', c) for c in creators]
        out.append(Candidate(
            'BnF', name,
            authors=creators[:3],
            year=_year(pick('date')),
            publisher=pick('publisher'),
            tags=pick('subject', True)[:8],
            comments=pick('description'),
            languages=[pick('language')] if pick('language') else [],
            kind='book'))
    return out


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

PROVIDERS = (
    # (key, label, function, kind, enabled by default)
    ('anilist', 'AniList', anilist, 'manga', True),
    ('mangadex', 'MangaDex', mangadex, 'manga', True),
    ('kitsu', 'Kitsu', kitsu, 'manga', True),
    ('jikan', 'MyAnimeList', jikan, 'manga', False),
    ('openlibrary', 'Open Library', openlibrary, 'book', True),
    ('bnf', 'BnF', bnf, 'book', True),
)

PROVIDERS_BY_KEY = {key: entry for entry, key in
                    ((entry, entry[0]) for entry in PROVIDERS)}


def run(keys, fetch, title, authors=None, log=None):
    """Run the selected providers, collecting whatever survives."""
    found = []
    for key in keys:
        entry = PROVIDERS_BY_KEY.get(key)
        if entry is None:
            continue
        _key, label, function, _kind, _default = entry
        try:
            results = function(fetch, title, authors, log) or []
        except Exception as err:
            if log is not None:
                log.error('%s failed: %s' % (label, err))
            continue
        if log is not None:
            log.info('%s: %d result(s)' % (label, len(results)))
        found.extend(results)
    return found
