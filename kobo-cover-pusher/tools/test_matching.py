#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test how library books are paired with the copies on the device.

    python tools/test_matching.py

No calibre and no device needed: the device books are stand-in objects.
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
                     'kobo_cover_pusher', 'matching.py')
_spec = importlib.util.spec_from_file_location('kcp_matching', _PATH)
matching = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(matching)

DeviceIndex = matching.DeviceIndex


class FakeDeviceBook(object):
    def __init__(self, title, authors, uuid=None, lpath=None):
        self.title = title
        self.authors = authors
        self.uuid = uuid
        self.lpath = lpath or ('books/%s.epub' % title.replace(' ', '_'))


DEVICE = [
    FakeDeviceBook('Shadow Slave', ['Guiltythree'], uuid='uuid-shadow'),
    FakeDeviceBook('Le dernier jour d’un condamné', ['Victor Hugo'],
                   uuid='uuid-hugo'),
    FakeDeviceBook('La guerre du pavot', ['R. F. Kuang'], uuid=None),
    # two different books sharing a title: never guess between them
    FakeDeviceBook('Vagabond', ['Takehiko Inoue'], uuid=None),
    FakeDeviceBook('Vagabond', ['Someone Else'], uuid=None),
]

# (label, uuid, title, authors, uuid_only, expected device title or None, how)
CASES = [
    ('uuid wins', 'uuid-shadow', 'Renamed In Calibre', ['Nobody'], False,
     'Shadow Slave', 'uuid'),
    ('accents and apostrophes', None, "Le dernier jour d'un condamne",
     ['Victor Hugo'], False, 'Le dernier jour d’un condamné', 'title and author'),
    ('title and author', None, 'La guerre du pavot', ['R. F. Kuang'], False,
     'La guerre du pavot', 'title and author'),
    ('author differs, title unique', None, 'La guerre du pavot', ['Autre'],
     False, 'La guerre du pavot', 'title only'),
    ('ambiguous title', None, 'Vagabond', ['Unknown Author'], False,
     None, 'several books share that title'),
    ('exact pair beats ambiguity', None, 'Vagabond', ['Takehiko Inoue'],
     False, 'Vagabond', 'title and author'),
    ('absent', None, 'Dune', ['Frank Herbert'], False,
     None, 'not on the device'),
    ('uuid only mode', None, 'La guerre du pavot', ['R. F. Kuang'], True,
     None, 'no uuid match'),
]


def main():
    index = DeviceIndex(DEVICE)
    print('%d device books indexed' % len(index))
    failures = []
    for label, uuid, title, authors, uuid_only, want_title, want_how in CASES:
        book, how = index.find(uuid, title, authors, uuid_only=uuid_only)
        got_title = book.title if book is not None else None
        if (got_title, how) != (want_title, want_how):
            failures.append('%s\n      got      %r via %r\n      expected %r '
                            'via %r' % (label, got_title, how, want_title,
                                        want_how))
        print('   %-28s -> %-32s (%s)'
              % (label, got_title or 'no match', how))

    keys = [('Ábc, dEf!', 'abc def'), ('  a  b  ', 'a b'), ('', '')]
    for raw, expected in keys:
        if matching.normalise(raw) != expected:
            failures.append('normalise(%r) = %r, expected %r'
                            % (raw, matching.normalise(raw), expected))

    print('\n%d cases' % (len(CASES) + len(keys)))
    if failures:
        print('%d FAILURE(S):' % len(failures))
        for f in failures:
            print('  ', f)
        return 1
    print('all passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
