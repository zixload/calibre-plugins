#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build every dialog once, without starting calibre, to catch Qt API mistakes.

    calibre-debug tools/gui_smoke.py

Nothing is shown on screen and no setting is written.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from calibre.gui2 import Application

from calibre_plugins.stylish_covers.config import ConfigWidget, get_settings
from calibre_plugins.stylish_covers.generator import BookInfo
from calibre_plugins.stylish_covers.widgets import PreviewDialog


def main():
    app = Application([])  # noqa: F841 - needed for widget construction

    settings = get_settings()
    print('settings loaded: %d keys, preset=%s'
          % (len(settings), settings.get('preset')))

    widget = ConfigWidget()
    print('ConfigWidget OK, %d tabs' % widget.tabs.count())
    collected = widget._collect()
    missing = [k for k in settings if k not in collected]
    print('ConfigWidget round trip OK, unmapped keys: %s' % (missing or 'none'))

    entries = [
        {'book_id': 1, 'image': None,
         'info': BookInfo('The Immortal Who Devoured the Heavens',
                          'Gu Zhen Ren', 'Reverend Insanity', 3, '蛊真人')},
        {'book_id': 2, 'image': None,
         'info': BookInfo('Shadow Slave', 'Guiltythree')},
    ]
    dialog = PreviewDialog(None, entries, settings)
    print('PreviewDialog OK, preview pixmap: %s'
          % (not dialog.preview_label.pixmap().isNull()))
    dialog.collect_settings()
    dialog._step(1)
    print('navigation OK, entry 2 = %s' % dialog._current()['info'].title)
    return 0


if __name__ == '__main__':
    sys.exit(main())
