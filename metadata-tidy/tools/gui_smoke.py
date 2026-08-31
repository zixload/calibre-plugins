#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build the dialogs once, without starting calibre, to catch Qt API mistakes.

    calibre-debug tools/gui_smoke.py

Nothing is shown on screen and no setting is written.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import calibre.customize.ui  # noqa: F401  installs the plugin import hook
from calibre.gui2 import Application

from calibre_plugins.metadata_tidy.config import ConfigWidget, get_settings
from calibre_plugins.metadata_tidy.parser import Proposal, parse_title
from calibre_plugins.metadata_tidy.widgets import TidyPreviewDialog


def main():
    app = Application([])  # noqa: F841 needed to build widgets

    settings = get_settings()
    print('settings: %d keys' % len(settings))

    widget = ConfigWidget()
    round_trip = widget._collect()
    missing = [k for k in settings if k not in round_trip]
    print('ConfigWidget OK, unmapped keys: %s' % (missing or 'none'))

    proposals = []
    for book_id, title in enumerate(['La guerre du pavot T1',
                                     'Vagabond part 02',
                                     'Berserk Tome II'], start=1):
        parsed = parse_title(title)
        p = Proposal(book_id, title, '', None, 'Someone')
        p.new_title, p.new_series = parsed.title, parsed.series
        p.new_index, p.rule = parsed.index, parsed.rule
        proposals.append(p)

    dialog = TidyPreviewDialog(None, proposals, 12)
    print('TidyPreviewDialog OK, %d rows, %d selected'
          % (dialog.table.rowCount(), len(dialog.selected_proposals())))
    dialog._set_all(False)
    print('select none -> %d selected, Apply enabled: %s'
          % (len(dialog.selected_proposals()), dialog.apply_button.isEnabled()))
    dialog._invert()
    print('invert -> %d selected' % len(dialog.selected_proposals()))
    if app:
        app.processEvents()
    dialog.grab().save('docs/preview-dialog.png')
    print('screenshot saved')
    return 0


if __name__ == '__main__':
    sys.exit(main())
