#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exercise the database path on a throwaway calibre library: read a cover,
generate, back up, write back, then restore.

    calibre-debug tools/library_roundtrip.py

Creates and deletes its own library in the temp folder; your own libraries are
never touched.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shutil
import sys
import tempfile

from calibre.db.legacy import LibraryDatabase
from calibre.ebooks.metadata.book.base import Metadata

from calibre_plugins.stylish_covers import backup
from calibre_plugins.stylish_covers.generator import (BookInfo,
                                                               merged_settings,
                                                               render_cover_bytes)
from calibre_plugins.stylish_covers.imageops import placeholder, to_bytes


def main():
    tmp = tempfile.mkdtemp(prefix='scg_lib_')
    try:
        db = LibraryDatabase(tmp).new_api
        library_id = 'roundtrip-test'

        mi = Metadata('The Immortal Who Devoured the Heavens', ['Gu Zhen Ren'])
        mi.series = 'Reverend Insanity'
        mi.series_index = 3
        book_id = db.add_books([(mi, {})])[0][0]

        original = to_bytes(placeholder(600, 900, (120, 40, 40), (20, 8, 8)))
        db.set_cover({book_id: original})
        stored = db.cover(book_id)
        print('cover written and read back: %d bytes' % len(stored))

        # what action.build_entry does
        meta = db.get_metadata(book_id)
        info = BookInfo(title=meta.title, authors=' & '.join(meta.authors),
                        series=meta.series, series_index=meta.series_index)
        print('metadata: %r / %r / %s #%s'
              % (info.title, info.authors, info.series, info.series_index))

        # what action._apply does
        data = render_cover_bytes(db.cover(book_id), info,
                                  merged_settings({'width': 800, 'height': 1200}))
        backup.store(library_id, book_id, stored, 'orig')
        backup.store(library_id, book_id, stored, 'prev')
        db.set_cover({book_id: data})
        generated = db.cover(book_id)
        print('generated cover applied: %d bytes, differs: %s'
              % (len(generated), generated != stored))

        # what action._restore does
        restored = backup.load(library_id, book_id, 'prev')
        db.set_cover({book_id: restored})
        back = db.cover(book_id)
        print('restore previous: %s' % ('identical to original'
                                        if back == stored else 'MISMATCH'))
        ok = back == stored

        # a custom column update, as the "mark column" option does
        db.create_custom_column('cover_style', 'Cover style', 'text', False)
        db.close()
        db = LibraryDatabase(tmp).new_api
        db.set_field('#cover_style', {book_id: 'dark_fantasy'})
        print('custom column: %r' % db.field_for('#cover_style', book_id))
        ok = ok and db.field_for('#cover_style', book_id) == 'dark_fantasy'

        for kind in ('prev', 'orig'):
            backup.discard(library_id, book_id, kind)
        db.close()
        print('OK' if ok else 'FAILED')
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
