#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the conversion rules, and check the header against the sample file
Goodreads publishes.

    python tools/test_exporter.py
    python tools/test_exporter.py --sample "C:/.../sample_export.csv"

Plain python: no calibre needed.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import datetime
import importlib.util
import io
import os
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'goodreads_export', 'exporter.py')
_spec = importlib.util.spec_from_file_location('gr_exporter', _PATH)
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)


def check(failures, label, got, expected):
    if got != expected:
        failures.append('%s\n      got      %r\n      expected %r'
                        % (label, got, expected))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample')
    args = ap.parse_args()
    failures = []

    # -- ratings: calibre stores 0..10, Goodreads wants 0..5 ---------------
    # calibre's scale is 0..10: 10 is five stars, 5 is two and a half
    for value, expected in ((0, ''), (None, ''), (10, '5'), (9, '5'), (8, '4'),
                            (7, '4'), (6, '3'), (5, '3'), (4.0, '2'),
                            (2, '1'), (1, '1'), ('6', '3')):
        check(failures, 'rating %r' % value, E.rating_to_goodreads(value),
              expected)

    # -- dates -------------------------------------------------------------
    check(failures, 'date', E.date_of(datetime.date(2024, 3, 7)), '2024-03-07')
    check(failures, 'date string', E.date_of('2019-11-02T08:00:00+01:00'),
          '2019-11-02')
    check(failures, 'undefined date', E.date_of(datetime.date(101, 1, 1)), '')
    check(failures, 'no date', E.date_of(None), '')
    check(failures, 'year', E.year_of(datetime.date(1746, 1, 1)), '1746')
    check(failures, 'undefined year', E.year_of(datetime.date(101, 1, 1)), '')

    # -- ISBN --------------------------------------------------------------
    check(failures, 'isbn hyphens', E.clean_isbn('978-1-58977-037-9'),
          '9781589770379')
    check(failures, 'isbn X', E.clean_isbn('043942089x'), '043942089X')
    check(failures, 'isbn junk', E.clean_isbn('n/a'), '')
    check(failures, 'isbn short', E.clean_isbn('12345'), '')

    # -- shelves -----------------------------------------------------------
    check(failures, 'shelf name', E.shelf_name('Science Fiction & Fantasy'),
          'science-fiction-&-fantasy')
    check(failures, 'shelf comma stripped', E.shelf_name('Fiction, general'),
          'fiction-general')
    exclusive, others = E.split_shelves(['Fiction', 'read', 'Drama'])
    check(failures, 'exclusive shelf from tags', exclusive, 'read')
    check(failures, 'other shelves', others, ['fiction', 'drama'])
    exclusive, others = E.split_shelves(['Fiction'], 'currently-reading')
    check(failures, 'exclusive from the column wins', exclusive,
          'currently-reading')

    # -- a whole book ------------------------------------------------------
    book = {
        'title': 'Candide, ou l’Optimisme', 'authors': ['Voltaire'],
        'isbn': '978-2-07-036000-0', 'rating': 8, 'publisher': 'Gallimard',
        'pubdate': datetime.date(1759, 1, 1),
        'timestamp': datetime.date(2026, 8, 31),
        'tags': ['Classics', 'read', 'Satire'],
        'comments': '<p>A <b>short</b> tale.</p>',
    }
    row = E.book_to_row(book, {'include_review': True})
    check(failures, 'title', row['Title'], 'Candide, ou l’Optimisme')
    check(failures, 'author', row['Author'], 'Voltaire')
    check(failures, 'rating', row['My Rating'], '4')
    check(failures, 'year published', row['Year Published'], '1759')
    check(failures, 'date added', row['Date Added'], '2026-08-31')
    check(failures, 'exclusive shelf', row['Shelves'], 'read')
    check(failures, 'bookshelves', row['Bookshelves'], 'classics satire')
    check(failures, 'review stripped', row['My Review'], 'A short tale.')

    # -- books Goodreads could never match are dropped ---------------------
    rows, skipped = E.rows_for([
        book,
        {'title': 'No author, no isbn', 'authors': [], 'tags': []},
        {'title': '', 'authors': ['Nobody']},
    ])
    check(failures, 'exportable rows', len(rows), 1)
    check(failures, 'skipped', len(skipped), 2)

    # -- the header must match the file Goodreads hands out ----------------
    if args.sample and os.path.isfile(args.sample):
        with io.open(args.sample, encoding='utf-8-sig') as f:
            sample = next(csv.reader(f))
        theirs = [c.strip() for c in sample]
        if theirs != E.COLUMNS:
            failures.append('header differs from the Goodreads sample\n'
                            '      sample %r\n      ours   %r'
                            % (theirs, E.COLUMNS))
        else:
            print('header matches the Goodreads sample: %d columns'
                  % len(theirs))

    # -- and the file we write must read back identically ------------------
    buf = io.StringIO()
    E.write_csv(buf, rows)
    buf.seek(0)
    back = list(csv.DictReader(buf))
    check(failures, 'round trip rows', len(back), 1)
    check(failures, 'round trip title', back[0]['Title'],
          'Candide, ou l’Optimisme')

    print('all rules checked')
    if failures:
        print('\n%d FAILURE(S):' % len(failures))
        for f in failures:
            print('  ', f)
        return 1
    print('all passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
