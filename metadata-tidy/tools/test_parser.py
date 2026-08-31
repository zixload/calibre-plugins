#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the title parser. Plain python, calibre not needed:

    python tools/test_parser.py

Add --library "C:\\path\\to\\Calibre Library" to also dry run the parser over a
real library, read only, and eyeball what it would propose.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import os
import sqlite3
import sys

# book titles are printed, and the Windows console is rarely UTF-8
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# parser.py is loaded straight from its file: importing the package would pull
# in __init__.py, which needs calibre, and the whole point here is to test the
# rules with nothing but the standard library.
import importlib.util  # noqa: E402

_PARSER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'metadata_tidy', 'parser.py')
_spec = importlib.util.spec_from_file_location('mdt_parser', _PARSER)
parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parser)

format_index = parser.format_index
parse_title = parser.parse_title
roman_to_int = parser.roman_to_int
swap_author = parser.swap_author

# (title, expected new title, expected series, expected index)
POSITIVE = [
    ('La guerre du pavot T1', 'La guerre du pavot', 'La guerre du pavot', 1),
    ('La Guerre du pavot, Livre 2 : La République du Dragon',
     'La République du Dragon', 'La Guerre du pavot', 2),
    ('Vagabond part 02', 'Vagabond', 'Vagabond', 2),
    ('Vagabond part 03', 'Vagabond', 'Vagabond', 3),
    ("86—EIGHTY-SIX: Alter, Vol. 1: The Reaper's Occasional Adolescence",
     "The Reaper's Occasional Adolescence", '86—EIGHTY-SIX: Alter', 1),
    ('The Poppy War (The Poppy War #1)', 'The Poppy War', 'The Poppy War', 1),
    ('Mistborn #2', 'Mistborn', 'Mistborn', 2),
    ('Dune, Book 3', 'Dune', 'Dune', 3),
    ('Berserk Tome II', 'Berserk', 'Berserk', 2),
    ('Le Trone de Fer, Tome 4 : L’Ascension', 'L’Ascension',
     'Le Trone de Fer', 4),
    ('Shadow Slave Vol. 1.5', 'Shadow Slave', 'Shadow Slave', 1.5),
    ('Kingdom, T. 12', 'Kingdom', 'Kingdom', 12),
    ('Solo Leveling (Solo Leveling, Book 4)', 'Solo Leveling',
     'Solo Leveling', 4),
    ('Vinland Saga n° 7', 'Vinland Saga', 'Vinland Saga', 7),
]

# Titles that must be left strictly alone
NEGATIVE = [
    'Fahrenheit 451',
    '1984',
    "Candide, ou l'Optimisme",
    'Le Prince cruel',
    'Les entretiens de confucius',
    'Lord of the Mysteries',
    '소년이 온다',
    'Boule de Suif et autres nouvelles',
    'Pensées pour moi-même',
    'Le colonel Chabert',
    'Le dernier jour d’un condamné',
    'Vingt mille lieues sous les mers',
    'Catch 22',
    'Slaughterhouse-Five',
    'La Peste',
]

ROMANS = [('i', 1), ('iv', 4), ('ix', 9), ('xii', 12), ('xxxix', 39),
          ('', None), ('abc', None)]

SWAPS = [('Hugo, Victor', 'Victor Hugo'),
         ('Victor Hugo', 'Victor Hugo'),
         ('Kuang, R. F.', 'R. F. Kuang'),
         ('Smith, Jr.', 'Smith, Jr.'),
         ('Inoue, Takehiko', 'Takehiko Inoue')]


def check(failures, label, got, expected):
    if got != expected:
        failures.append('%s\n      got      %r\n      expected %r'
                        % (label, got, expected))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--library')
    args = ap.parse_args()

    failures = []

    for numeral, expected in ROMANS:
        check(failures, 'roman %r' % numeral, roman_to_int(numeral), expected)

    for name, expected in SWAPS:
        check(failures, 'swap %r' % name, swap_author(name), expected)

    for title, want_title, want_series, want_index in POSITIVE:
        got = parse_title(title)
        if got is None:
            failures.append('%r\n      got      None\n      expected %r #%s'
                            % (title, want_series, want_index))
            continue
        check(failures, repr(title),
              (got.title, got.series, got.index),
              (want_title, want_series, float(want_index)))

    for title in NEGATIVE:
        got = parse_title(title)
        if got is not None:
            failures.append('%r must not match, got %r' % (title, got))

    print('%d positive, %d negative, %d roman, %d author cases'
          % (len(POSITIVE), len(NEGATIVE), len(ROMANS), len(SWAPS)))
    if failures:
        print('\n%d FAILURE(S):' % len(failures))
        for f in failures:
            print('  ', f)
    else:
        print('all passed')

    if args.library:
        print('\nDry run over %s' % args.library)
        db = sqlite3.connect(os.path.join(args.library, 'metadata.db'))
        rows = db.execute('select title from books order by title').fetchall()
        hits = 0
        for (title,) in rows:
            got = parse_title(title)
            if got:
                hits += 1
                print('   %-52s -> %-28s %s #%s'
                      % (title[:52], got.title[:28], got.series,
                         format_index(got.index)))
            else:
                print('   %-52s    (left alone)' % title[:52])
        print('   %d/%d titles would change' % (hits, len(rows)))

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
