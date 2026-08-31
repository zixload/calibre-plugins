#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The candidate records returned by each API, and how they are cross-checked.

Pure python: no calibre, no network.  Everything here can be exercised from a
plain prompt with hand written candidates, which is how the merging rules are
tested.

The rule that shapes all of this: **fill generously, flag honestly**.  A field
seen by a single source is still filled in, because the user reviews the
result in calibre's own download dialog; agreement between sources only
decides which candidate is offered first and what the confidence line says.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)
_SPACE = re.compile(r'\s+', re.UNICODE)
# volume markers must not make two volumes of one work look like one book
_VOLUME = re.compile(r'\b(?:vol|volume|tome|livre|book|part|partie|t)\.?\s*\d+\b',
                     re.IGNORECASE)


def normalise(text):
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = _PUNCT.sub(' ', text.lower())
    return _SPACE.sub(' ', text).strip()


def title_key(title):
    """Comparison key: accents, punctuation, case and volume markers removed."""
    return _SPACE.sub(' ', _VOLUME.sub(' ', normalise(title))).strip()


def similar(a, b):
    """How likely two titles name the same work, between 0 and 1.

    Token overlap alone breaks on romanisation: "Gu Zhenren" and "Gu Zhen Ren"
    share one word out of two or three.  Comparing the space free strings as
    well catches exactly that, and the two measures are combined by taking
    whichever is more generous.
    """
    ka, kb = title_key(a), title_key(b)
    if not ka or not kb:
        return 0.0
    ta, tb = set(ka.split()), set(kb.split())
    overlap = len(ta & tb) / float(min(len(ta), len(tb))) if ta and tb else 0.0
    ratio = SequenceMatcher(None, ka.replace(' ', ''),
                            kb.replace(' ', '')).ratio()
    return max(overlap, ratio)


class Candidate(object):
    """One API's answer about one work."""

    FIELDS = ('title', 'native_title', 'authors', 'year', 'publisher', 'tags',
              'comments', 'series', 'series_index', 'languages', 'cover_url',
              'url', 'kind')

    def __init__(self, source, title, **kwargs):
        self.source = source
        self.title = (title or '').strip()
        self.native_title = kwargs.get('native_title') or ''
        self.authors = [a for a in (kwargs.get('authors') or []) if a]
        self.year = kwargs.get('year')
        self.publisher = kwargs.get('publisher') or ''
        self.tags = [t for t in (kwargs.get('tags') or []) if t]
        self.comments = kwargs.get('comments') or ''
        self.series = kwargs.get('series') or ''
        self.series_index = kwargs.get('series_index')
        self.languages = [x for x in (kwargs.get('languages') or []) if x]
        self.identifiers = dict(kwargs.get('identifiers') or {})
        self.cover_url = kwargs.get('cover_url') or ''
        self.url = kwargs.get('url') or ''
        # "manga" covers manga, manhwa, manhua, light novels and web novels;
        # "book" is everything a library catalogue knows about
        self.kind = kwargs.get('kind') or 'book'

    def __repr__(self):
        return 'Candidate(%s, %r, %s)' % (self.source, self.title, self.year)


def cluster(candidates, threshold=0.6):
    """Group candidates that talk about the same work."""
    groups = []
    for candidate in candidates:
        if not candidate.title:
            continue
        for group in groups:
            if similar(group[0].title, candidate.title) >= threshold:
                group.append(candidate)
                break
        else:
            groups.append([candidate])
    groups.sort(key=lambda g: (-len({c.source for c in g}), -len(g)))
    return groups


def _vote(values, key=None):
    """Most agreed upon value, ties broken by first seen.

    *key* normalises before comparing: three sources writing the same title as
    "86: Eighty Six", "86-EIGHTY-SIX" and "86―EIGHTY-SIX―" do agree, and the
    confidence line must say so.
    """
    values = [v for v in values if v not in (None, '', [])]
    if not values:
        return None, 0
    key = key or (lambda v: str(v))
    counts = Counter(key(v) for v in values)
    best, hits = counts.most_common(1)[0]
    for value in values:
        if key(value) == best:
            return value, hits
    return values[0], hits


class Merged(object):
    """What the cross-check produced for one work."""

    def __init__(self):
        self.title = ''
        self.native_title = ''
        self.authors = []
        self.year = None
        self.publisher = ''
        self.tags = []
        self.comments = ''
        self.series = ''
        self.series_index = None
        self.languages = []
        self.identifiers = {}
        self.cover_url = ''
        self.sources = []
        self.agreement = {}
        self.urls = []

    @property
    def confidence(self):
        """How many distinct sources backed the title."""
        return self.agreement.get('title', 0)


def merge(group, max_tags=12):
    """Cross-check one cluster into a single record."""
    out = Merged()
    out.sources = sorted({c.source for c in group})
    by_source = {}
    for candidate in group:
        by_source.setdefault(candidate.source, candidate)
    unique = list(by_source.values())

    keys = {'title': title_key, 'publisher': normalise, 'series': title_key,
            'native_title': normalise}
    for field in ('title', 'publisher', 'series', 'year', 'native_title',
                  'series_index'):
        value, hits = _vote([getattr(c, field) for c in unique],
                            keys.get(field))
        if value is not None:
            setattr(out, field, value)
            out.agreement[field] = hits

    # authors: keep the set the most sources agree on, else the longest list
    author_sets = [c.authors for c in unique if c.authors]
    value, hits = _vote(author_sets,
                        lambda names: '|'.join(sorted(normalise(n)
                                                      for n in names)))
    if value:
        out.authors = list(value)
        out.agreement['authors'] = hits

    # tags and languages are unions: more is better, the user prunes
    tags, seen = [], set()
    for candidate in unique:
        for tag in candidate.tags:
            key = normalise(tag)
            if key and key not in seen:
                seen.add(key)
                tags.append(tag)
    out.tags = tags[:max_tags]

    # languages are voted on, not unioned: a spanish and a french edition in
    # the results must not make a japanese manga trilingual
    language, hits = _vote([c.languages[0] for c in unique if c.languages])
    if language:
        out.languages = [language]
        out.agreement['languages'] = hits

    # the longest description wins: it is the most informative
    descriptions = [(len(c.comments), c.source, c.comments)
                    for c in unique if c.comments]
    if descriptions:
        out.comments = max(descriptions)[2]

    covers = [c.cover_url for c in unique if c.cover_url]
    out.cover_url = covers[0] if covers else ''
    out.urls = [c.url for c in unique if c.url]

    for candidate in unique:
        out.identifiers.update(candidate.identifiers)
    return out


def confidence_note(merged):
    """One human readable line saying who confirmed what."""
    if not merged.sources:
        return ''
    agreed = [name for name, hits in sorted(merged.agreement.items())
              if hits > 1]
    line = 'Cross-check: %d source(s) - %s.' % (len(merged.sources),
                                                ', '.join(merged.sources))
    if agreed:
        line += ' Agreed on: %s.' % ', '.join(agreed)
    else:
        line += ' No field was confirmed twice, so treat it as a single source.'
    return line


def cross_check(candidates, threshold=0.6, searched=None, min_overlap=0.34):
    """Full pipeline: cluster, merge, drop the obvious noise, best first.

    A catalogue answering a manga query with an unrelated record is common;
    such a record shares almost no word with what was searched and is backed
    by a single source, so it is dropped.  Anything two sources agree on is
    kept whatever its title looks like.
    """
    results = [merge(group) for group in cluster(candidates, threshold)]
    if searched:
        results = [m for m in results
                   if len(m.sources) > 1 or similar(m.title, searched) >= min_overlap]
    results.sort(key=lambda m: (-len(m.sources), -len(m.comments)))
    return results
