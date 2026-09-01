#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hostile metadata against every preset: nothing here is allowed to raise, and
no text is allowed to spill outside the canvas.

    calibre-debug tools/edge_cases.py
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from stylish_covers import presets as presets_mod  # noqa: E402
from stylish_covers.generator import (BookInfo, merged_settings,  # noqa: E402
                                               render_cover)

CASES = [
    ('empty', BookInfo()),
    ('no author', BookInfo('A Title With No Author At All')),
    ('one word', BookInfo('Antidisestablishmentarianismophobia', 'X')),
    ('unbreakable', BookInfo('A' * 60, 'Y')),
    ('very long', BookInfo('The Exceedingly Long And Frankly Unreasonable '
                           'Chronicle Of A Cultivator Who Refused To Die '
                           'Even Once', 'Someone With A Very Long Pen Name',
                           'An Equally Long Series Name', 12)),
    ('cjk only', BookInfo('蛊真人', '古真人', asian_title='蛊真人')),
    ('mixed', BookInfo('Reverend 蛊真人 Insanity', 'Gu Zhen Ren',
                       asian_title='그림자 노예 転生')),
    ('newlines', BookInfo('Line One\nLine Two\nLine Three', 'Z')),
    ('half index', BookInfo('Interlude', 'Author', 'Series', 2.5)),
    ('symbols', BookInfo('★ Rise & Fall — Vol. 1 (Reborn) ★', 'A. B. Çelik')),
]

SIZES = [(1600, 2400), (800, 1200), (1200, 1200)]


def main():
    failures = 0
    checked = 0
    for preset in presets_mod.BUILTIN_PRESETS:
        for label, info in CASES:
            width, height = SIZES[checked % len(SIZES)]
            settings = merged_settings({
                'preset': preset['id'], 'width': width, 'height': height,
                'asian_enabled': True,
            })
            checked += 1
            try:
                image = render_cover(None, info, settings)
            except Exception as err:
                failures += 1
                print('FAIL %-14s %-12s %s: %s'
                      % (preset['id'], label, type(err).__name__, err))
                continue
            if image.size != (width, height):
                failures += 1
                print('FAIL %-14s %-12s wrong size %s'
                      % (preset['id'], label, (image.size,)))
    print('%d renders, %d failures' % (checked, failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
