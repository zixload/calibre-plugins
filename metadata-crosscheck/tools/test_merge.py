#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the cross-checking rules with hand written candidates.

    python tools/test_merge.py

No calibre, no network.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib.util
import os
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'metadata_crosscheck', 'candidates.py')
_spec = importlib.util.spec_from_file_location('mcc_candidates', _PATH)
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

Candidate = C.Candidate


def check(failures, label, got, expected):
    if got != expected:
        failures.append('%s\n      got      %r\n      expected %r'
                        % (label, got, expected))


def main():
    failures = []

    # three spellings of one title must count as agreement, not as three works
    group = [
        Candidate('AniList', '86: Eighty Six', native_title='86―エイティシックス―',
                  year=2018, authors=['Motoki Yoshihara'], tags=['Action'],
                  languages=['jpn'], comments='short'),
        Candidate('MangaDex', '86—EIGHTY-SIX', native_title='86―エイティシックス―',
                  year=2018, authors=['Motoki Yoshihara'], tags=['Mecha'],
                  languages=['jpn'], comments='a much longer description here'),
        Candidate('BnF', '86 EIGHTY SIX', year=2018, publisher='Delcourt-Tonkam',
                  tags=['Action'], languages=['fre']),
    ]
    merged = C.cross_check(group)
    check(failures, 'one work, not three', len(merged), 1)
    record = merged[0]
    check(failures, 'title agreed by 3', record.agreement.get('title'), 3)
    check(failures, 'year agreed by 3', record.agreement.get('year'), 3)
    check(failures, 'publisher taken from the only source that has one',
          record.publisher, 'Delcourt-Tonkam')
    check(failures, 'native title kept', record.native_title, '86―エイティシックス―')
    check(failures, 'tags unioned', sorted(record.tags), ['Action', 'Mecha'])
    check(failures, 'longest description wins', record.comments,
          'a much longer description here')
    check(failures, 'language voted, not unioned', record.languages, ['jpn'])
    check(failures, 'sources listed', record.sources,
          ['AniList', 'BnF', 'MangaDex'])

    # volumes of one work are one work; unrelated titles are not
    check(failures, 'volume markers ignored',
          C.title_key('Vagabond Vol. 3'), C.title_key('Vagabond'))
    check(failures, 'different works stay apart',
          len(C.cluster([Candidate('a', 'Vagabond'),
                         Candidate('b', 'Rurouni Kenshin')])), 2)

    # a single source answering something unrelated is dropped
    noisy = [Candidate('AniList', 'Lord of the Mysteries', year=2020),
             Candidate('BnF', 'Vier / Perfect beings', year=2018)]
    kept = C.cross_check(noisy, searched='Lord of the Mysteries')
    check(failures, 'unrelated single source dropped', len(kept), 1)
    # but two agreeing sources are kept even with an unfamiliar title
    agreed = [Candidate('AniList', 'Gu Zhenren', year=2012),
              Candidate('MangaDex', 'Gu Zhen Ren', year=2012)]
    check(failures, 'two sources kept regardless of the searched title',
          len(C.cross_check(agreed, searched='Reverend Insanity')), 1)

    note = C.confidence_note(record)
    if 'AniList' not in note or 'Agreed on' not in note:
        failures.append('confidence note unhelpful: %r' % note)
    print('confidence line: %s' % note)

    print('\n%d checks' % (13,))
    if failures:
        print('%d FAILURE(S):' % len(failures))
        for f in failures:
            print('  ', f)
        return 1
    print('all passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
