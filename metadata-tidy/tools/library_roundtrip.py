#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Full cycle on a throwaway calibre library: propose, apply, verify, undo,
verify again.

    calibre-debug tools/library_roundtrip.py

Your own libraries are never touched.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import shutil
import sys
import tempfile

from calibre.db.legacy import LibraryDatabase
from calibre.ebooks.metadata.book.base import Metadata

from calibre_plugins.metadata_tidy import tidy
from calibre_plugins.metadata_tidy.config import DEFAULTS
from calibre_plugins.metadata_tidy.parser import format_index

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# (title, authors, expected series, expected index, expected new title)
BOOKS = [
    # Both spellings must converge on one, since calibre merges series names
    # case insensitively anyway; the volume 1 spelling is the one kept.
    ('La guerre du pavot T1', ['Kuang, R. F.'],
     'La guerre du pavot', 1, 'La guerre du pavot'),
    ('La Guerre du pavot, Livre 2 : La République du Dragon', ['Kuang, R. F.'],
     'La guerre du pavot', 2, 'La République du Dragon'),
    ('Vagabond part 02', ['Takehiko Inoue'], 'Vagabond', 2, 'Vagabond'),
    ("Candide, ou l'Optimisme", ['Voltaire'], '', None,
     "Candide, ou l'Optimisme"),
    ('Fahrenheit 451', ['Ray Bradbury'], '', None, 'Fahrenheit 451'),
    ('소년이 온다', ['Han Kang'], '', None, '소년이 온다'),
]


def main():
    tmp = tempfile.mkdtemp(prefix='mdt_lib_')
    failures = []
    try:
        db = LibraryDatabase(tmp).new_api
        ids = {}
        for title, authors, _s, _i, _t in BOOKS:
            mi = Metadata(title, list(authors))
            ids[title] = db.add_books([(mi, {})])[0][0]
        print('%d books added' % len(ids))

        settings = dict(DEFAULTS)
        proposals = tidy.build_proposals(db, list(ids.values()), settings)
        print('%d proposal(s):' % len(proposals))
        for p in proposals:
            print('   %-48s -> %-26s %s #%s'
                  % (p.old_title[:48], p.new_title[:26], p.new_series,
                     format_index(p.new_index)))

        expected_changes = sum(1 for b in BOOKS if b[2])
        if len(proposals) != expected_changes:
            failures.append('expected %d proposals, got %d'
                            % (expected_changes, len(proposals)))

        tidy.write_changes(db, proposals)
        undo = tidy.split_changes(proposals)[4]

        print('\nafter apply:')
        for title, _a, want_series, want_index, want_title in BOOKS:
            mi = db.get_metadata(ids[title])
            got = (mi.title, mi.series or '',
                   None if not mi.series else mi.series_index)
            want = (want_title, want_series,
                    None if not want_series else float(want_index))
            flag = 'ok ' if got == want else 'BAD'
            if got != want:
                failures.append('%r -> %r, expected %r' % (title, got, want))
            print('   %s %-40s %s' % (flag, got[0][:40],
                                      ('%s #%s' % (got[1], format_index(got[2])))
                                      if got[1] else '(no series)'))

        restored = tidy.restore(db, undo)
        print('\n%d book(s) restored' % len(restored))
        for title, authors, _s, _i, _t in BOOKS:
            mi = db.get_metadata(ids[title])
            if mi.title != title:
                failures.append('undo failed for %r, title is %r'
                                % (title, mi.title))
            if list(mi.authors) != list(authors):
                failures.append('undo failed for %r, authors are %r'
                                % (title, mi.authors))
            if mi.series:
                failures.append('undo left a series on %r: %r'
                                % (title, mi.series))
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print('\n%d FAILURE(S):' % len(failures))
        for f in failures:
            print('  ', f)
        return 1
    print('\nall good: proposals, apply and undo all behave')
    return 0


if __name__ == '__main__':
    sys.exit(main())
