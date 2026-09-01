#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pairing library books with the copies already on the device.

Pure python and duck typed on purpose: it works on anything exposing uuid,
title, authors and lpath, so the whole matching logic can be tested with
stand-in objects and no device.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re
import unicodedata

_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)
_SPACE = re.compile(r'\s+', re.UNICODE)


def normalise(text):
    """Casefolded, accent stripped, punctuation free key for fuzzy equality."""
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = _PUNCT.sub(' ', text.lower())
    return _SPACE.sub(' ', text).strip()


def authors_key(authors):
    """A stable key from a list of authors, or from an already joined string."""
    if isinstance(authors, str):
        names = re.split(r'\s*&\s*|\s*,\s*', authors)
    else:
        names = list(authors or [])
    return ' & '.join(sorted(normalise(n) for n in names if n))


def _attr(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return value
    return None


def title_author_key(title, authors):
    return '%s|%s' % (normalise(title), authors_key(authors))


class DeviceIndex(object):
    """Lookup tables over the books currently on the device."""

    def __init__(self, device_books):
        self.by_uuid = {}
        self.by_title_author = {}
        self.by_title = {}
        self.books = list(device_books or [])
        for book in self.books:
            uuid = _attr(book, 'uuid', 'application_id')
            if uuid:
                self.by_uuid.setdefault(str(uuid), book)
            title = _attr(book, 'title') or ''
            authors = getattr(book, 'authors', None) or []
            if title:
                self.by_title_author.setdefault(
                    title_author_key(title, authors), book)
                # a title seen twice is ambiguous and must not be guessed at
                key = normalise(title)
                if key in self.by_title:
                    self.by_title[key] = None
                else:
                    self.by_title[key] = book

    def find(self, uuid, title, authors, uuid_only=False):
        """Return (device book, how) or (None, reason)."""
        if uuid and str(uuid) in self.by_uuid:
            return self.by_uuid[str(uuid)], 'uuid'
        if uuid_only:
            return None, 'no uuid match'
        key = title_author_key(title, authors)
        if key in self.by_title_author:
            return self.by_title_author[key], 'title and author'
        book = self.by_title.get(normalise(title))
        if book is not None:
            return book, 'title only'
        if normalise(title) in self.by_title:
            return None, 'several books share that title'
        return None, 'not on the device'

    def __len__(self):
        return len(self.books)
