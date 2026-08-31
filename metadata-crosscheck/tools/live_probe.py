#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hit the real APIs with real titles and show what each one answers, then what
the cross-check makes of it.

    python tools/live_probe.py            # a fixed sample
    python tools/live_probe.py "Vagabond" # one title

Plain python: no calibre needed.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    """Load a module by path: the package __init__ needs calibre."""
    path = os.path.join(ROOT, 'metadata_crosscheck', '%s.py' % name)
    spec = importlib.util.spec_from_file_location('mcc_%s' % name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


candidates = load('candidates')
sys.modules['metadata_crosscheck'] = type(sys)('metadata_crosscheck')
sys.modules['metadata_crosscheck'].candidates = candidates


def load_providers():
    path = os.path.join(ROOT, 'metadata_crosscheck', 'providers.py')
    source = open(path, encoding='utf-8').read().replace(
        'from .candidates import Candidate', '')
    module = type(sys)('mcc_providers')
    module.Candidate = candidates.Candidate
    exec(compile(source, path, 'exec'), module.__dict__)
    return module


providers = load_providers()

from urllib.request import Request, urlopen  # noqa: E402

UA = 'Mozilla/5.0 calibre Cross-Check probe'


def fetch(url, data=None, headers=None):
    merged = {'User-Agent': UA, 'Accept': 'application/json'}
    merged.update(headers or {})
    with urlopen(Request(url, data=data, headers=merged), timeout=20) as r:
        return r.read()


class Log(object):
    def info(self, *a):
        print('     ', *a)

    def error(self, *a):
        print('      ERROR', *a)


SAMPLE = [
    ('Vagabond', ['Takehiko Inoue']),
    ('Reverend Insanity', None),
    ('86 EIGHTY-SIX', None),
    ('Candide', ['Voltaire']),
    ('Le colonel Chabert', ['Balzac']),
]


def main():
    if len(sys.argv) > 1:
        sample = [(' '.join(sys.argv[1:]), None)]
    else:
        sample = SAMPLE
    keys = [p[0] for p in providers.PROVIDERS if p[4]]
    for title, authors in sample:
        print('\n=== %s' % title)
        found = providers.run(keys, fetch, title, authors, Log())
        merged = candidates.cross_check(found)
        for record in merged[:2]:
            print('   -> %-40s %s' % (record.title[:40],
                                      '[%s]' % ', '.join(record.sources)))
            print('      natif=%s annee=%s editeur=%s'
                  % (record.native_title or '-', record.year or '-',
                     record.publisher or '-'))
            print('      auteurs=%s' % (', '.join(record.authors) or '-'))
            print('      tags=%s' % (', '.join(record.tags[:6]) or '-'))
            print('      %s' % candidates.confidence_note(record))
    return 0


if __name__ == '__main__':
    sys.exit(main())
