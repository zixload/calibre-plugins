#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Turning library books into rows Goodreads will accept.

Pure python: no calibre, no Qt.  The caller hands plain dicts, so every
conversion rule below can be tested from a prompt.

The column names and their order come from the sample file Goodreads itself
publishes on its import page; the importer matches on those headers, so they
must be spelled exactly.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re

COLUMNS = ['Title', 'Author', 'ISBN', 'My Rating', 'Average Rating',
           'Publisher', 'Binding', 'Year Published',
           'Original Publication Year', 'Date Read', 'Date Added', 'Shelves',
           'Bookshelves', 'My Review']

# Goodreads keeps one "exclusive" shelf per book; everything else is a plain
# shelf listed in Bookshelves.
EXCLUSIVE_SHELVES = ('read', 'currently-reading', 'to-read')

_TAG_STRIP = re.compile(r'[",;]+')
_SPACES = re.compile(r'\s+')
_HTML_TAG = re.compile(r'<[^>]+>')
_ISBN_CLEAN = re.compile(r'[^0-9Xx]')


def clean_html(text, limit=0):
    """Strip markup and collapse whitespace; reviews travel as plain text."""
    if not text:
        return ''
    text = re.sub(r'<\s*br\s*/?>|</\s*p\s*>', '\n', text, flags=re.IGNORECASE)
    text = _HTML_TAG.sub('', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'")
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(' ', 1)[0] + '...'
    return text


def rating_to_goodreads(rating):
    """calibre stores 0..10, half a star each; Goodreads wants whole stars.

    Always halved: a calibre rating of 10 is five stars, 5 is two and a half.
    Guessing the scale from the value would read 5 as five stars, which is
    wrong by half the range.  Halves round up, the way a reader would.
    """
    try:
        value = float(rating or 0)
    except (TypeError, ValueError):
        return ''
    if value <= 0:
        return ''
    stars = value / 2.0
    stars = int(stars + 0.5)          # round half up, not to even
    return str(min(5, max(1, stars)))


def year_of(value):
    """Year from a date, a datetime or a string, or ''."""
    if value is None:
        return ''
    year = getattr(value, 'year', None)
    if year:
        return '' if year <= 101 else str(year)
    match = re.search(r'(\d{4})', str(value))
    if not match:
        return ''
    year = int(match.group(1))
    return '' if year <= 101 else str(year)


def date_of(value):
    """ISO day, the format Goodreads' own sample file uses."""
    if value is None:
        return ''
    year = getattr(value, 'year', None)
    if year is not None:
        # calibre writes year 101 for "undefined"
        if year <= 101:
            return ''
        try:
            return value.strftime('%Y-%m-%d')
        except ValueError:
            return ''
    match = re.match(r'\s*(\d{4})-(\d{2})-(\d{2})', str(value))
    if not match:
        return ''
    return '' if int(match.group(1)) <= 101 else '-'.join(match.groups())


def clean_isbn(value):
    """Keep digits and X; Goodreads rejects anything else."""
    if not value:
        return ''
    isbn = _ISBN_CLEAN.sub('', str(value)).upper()
    return isbn if len(isbn) in (10, 13) else ''


def shelf_name(tag):
    """A tag turned into something Goodreads accepts as a shelf.

    Shelf names are lowercase and cannot hold a comma, a quote or a
    semicolon; spaces become hyphens, the way Goodreads writes its own.
    """
    tag = _TAG_STRIP.sub('', str(tag or '')).strip().lower()
    tag = _SPACES.sub('-', tag)
    return tag.strip('-')[:60]


def split_shelves(tags, exclusive=None, max_shelves=12):
    """Return (exclusive shelf, other shelves) from a list of tags."""
    seen, others = set(), []
    found_exclusive = exclusive if exclusive in EXCLUSIVE_SHELVES else ''
    for tag in tags or ():
        name = shelf_name(tag)
        if not name or name in seen:
            continue
        seen.add(name)
        if name in EXCLUSIVE_SHELVES:
            # a tag saying "read" decides the exclusive shelf, unless the
            # caller already knows it from a dedicated column
            if not found_exclusive:
                found_exclusive = name
            continue
        others.append(name)
    return found_exclusive, others[:max_shelves]


def book_to_row(book, settings=None):
    """One library book as a dict keyed by the Goodreads column names."""
    settings = settings or {}
    authors = [a for a in (book.get('authors') or []) if a]
    exclusive, shelves = split_shelves(book.get('tags'),
                                       book.get('read_status'),
                                       int(settings.get('max_shelves', 12)))
    if not exclusive:
        exclusive = settings.get('default_shelf') or ''

    review = ''
    if settings.get('include_review'):
        review = clean_html(book.get('comments'),
                            int(settings.get('review_limit', 0) or 0))

    return {
        'Title': (book.get('title') or '').strip(),
        # Goodreads matches on a single author; the sample file has no column
        # for the others, so co-authors are dropped rather than jammed in
        'Author': authors[0] if authors else '',
        'ISBN': clean_isbn(book.get('isbn')),
        'My Rating': rating_to_goodreads(book.get('rating')),
        'Average Rating': '',
        'Publisher': (book.get('publisher') or '').strip(),
        'Binding': settings.get('binding') or '',
        'Year Published': year_of(book.get('pubdate')),
        'Original Publication Year': year_of(book.get('original_year')),
        'Date Read': date_of(book.get('date_read')),
        'Date Added': date_of(book.get('timestamp')),
        'Shelves': exclusive,
        'Bookshelves': ' '.join(shelves),
        'My Review': review,
    }


def rows_for(books, settings=None):
    """Every exportable book as a row; the ones without a title are skipped."""
    settings = settings or {}
    only_isbn = bool(settings.get('only_with_isbn'))
    rows, skipped = [], []
    for book in books:
        row = book_to_row(book, settings)
        if not row['Title']:
            skipped.append((book.get('title') or '?', 'no title'))
            continue
        if only_isbn and not row['ISBN']:
            skipped.append((row['Title'], 'no ISBN'))
            continue
        if not row['Author'] and not row['ISBN']:
            skipped.append((row['Title'],
                            'Goodreads needs an author or an ISBN to match'))
            continue
        rows.append(row)
    return rows, skipped


def write_csv(handle, rows):
    """Write the rows with the exact header Goodreads expects."""
    import csv
    writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction='ignore',
                            lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return len(rows)
