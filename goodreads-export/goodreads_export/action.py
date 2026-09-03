#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The calibre side: toolbar button, menu, reading the library and writing the
file.  Every conversion rule lives in exporter.py, which knows nothing about
calibre.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import io
import os
import traceback

from calibre.gui2 import choose_save_file, error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from qt.core import QIcon, QMenu, QToolButton

from . import exporter
from .config import get_settings

PLUGIN_NAME = 'Goodreads Export'
PLUGIN_ICON = 'images/icon.png'

READ_WORDS = {'read', 'lu', 'lue', 'fini', 'finished', 'done', 'true', 'yes'}
READING_WORDS = {'currently-reading', 'reading', 'en cours', 'en-cours'}
TOREAD_WORDS = {'to-read', 'toread', 'a lire', 'a-lire', 'wishlist'}


def _load_icon():
    try:
        return get_icons(PLUGIN_ICON, PLUGIN_NAME)  # noqa: F821 calibre builtin
    except Exception:
        return QIcon.ic('catalog.png') if hasattr(QIcon, 'ic') else QIcon()


def read_status_from(value):
    """Turn whatever a read column holds into a Goodreads exclusive shelf."""
    if value is None or value == '':
        return ''
    if value is True:
        return 'read'
    if value is False:
        return ''
    text = str(value).strip().lower().replace('_', '-')
    if text in READ_WORDS:
        return 'read'
    if text in READING_WORDS:
        return 'currently-reading'
    if text in TOREAD_WORDS:
        return 'to-read'
    return ''


class GoodreadsExportAction(InterfaceAction):

    name = PLUGIN_NAME
    action_spec = ('Goodreads Export', None,
                   'Write a CSV that Goodreads can import', ())
    action_type = 'current'
    popup_type = QToolButton.ToolButtonPopupMode.MenuButtonPopup
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        icon = _load_icon()
        self.qaction.setIcon(icon)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.qaction.triggered.connect(self.export_selected)

        m = self.menu
        self.create_menu_action(
            m, 'gre_selected', 'Export the selected books...', icon=icon,
            description='Write a Goodreads CSV for the current selection',
            triggered=self.export_selected)
        self.create_menu_action(
            m, 'gre_library', 'Export the whole library...', icon=icon,
            description='Write a Goodreads CSV for every book',
            triggered=self.export_library)
        m.addSeparator()
        self.create_menu_action(
            m, 'gre_settings', 'Settings...',
            description='Shelves, columns and what goes in the file',
            triggered=self.show_settings)

    def location_selected(self, loc):
        self.qaction.setEnabled(loc == 'library')

    def show_settings(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    # -- reading the library ----------------------------------------------
    def _db(self):
        return self.gui.current_db.new_api

    def book_dict(self, db, book_id, settings):
        """One book as the plain dict exporter.py expects."""
        mi = db.get_metadata(book_id)
        read_status = ''
        column = (settings.get('read_column') or '').strip()
        if column:
            try:
                read_status = read_status_from(mi.get(column, None))
            except Exception:
                read_status = ''
        date_read = None
        column = (settings.get('date_read_column') or '').strip()
        if column:
            try:
                date_read = mi.get(column, None)
            except Exception:
                date_read = None
        original_year = None
        column = (settings.get('original_year_column') or '').strip()
        if column:
            try:
                original_year = mi.get(column, None)
            except Exception:
                original_year = None

        return {
            'title': mi.title,
            'authors': list(mi.authors or []),
            'isbn': mi.isbn,
            'rating': mi.rating,
            'publisher': mi.publisher,
            'pubdate': mi.pubdate,
            'timestamp': mi.timestamp,
            'tags': list(mi.tags or []) if settings.get('shelf_from_tags', True)
                    else [],
            'comments': mi.comments,
            'read_status': read_status,
            'date_read': date_read,
            'original_year': original_year,
        }

    # -- actions -----------------------------------------------------------
    def export_selected(self, *args):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, PLUGIN_NAME,
                         'Select the books you want to export, or use '
                         '"Export the whole library".', show=True)
            return
        model = self.gui.library_view.model()
        self._export([model.id(row) for row in rows], 'selection')

    def export_library(self, *args):
        try:
            book_ids = sorted(self._db().all_book_ids())
        except Exception as err:
            error_dialog(self.gui, PLUGIN_NAME, 'Could not read the library.',
                         det_msg=str(err), show=True)
            return
        self._export(book_ids, 'library')

    def _export(self, book_ids, what):
        if not book_ids:
            error_dialog(self.gui, PLUGIN_NAME, 'There is nothing to export.',
                         show=True)
            return
        settings = get_settings()
        db = self._db()

        books = []
        for book_id in book_ids:
            try:
                books.append(self.book_dict(db, book_id, settings))
            except Exception:
                traceback.print_exc()
        rows, skipped = exporter.rows_for(books, settings)
        if not rows:
            error_dialog(
                self.gui, PLUGIN_NAME,
                'None of those %d book(s) can be exported.' % len(book_ids),
                det_msg='\n'.join('%s - %s' % s for s in skipped), show=True)
            return

        path = choose_save_file(
            self.gui, 'goodreads-export-path', 'Save the Goodreads CSV',
            filters=[('CSV files', ['csv'])],
            initial_filename='goodreads-%s.csv' % what)
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'

        try:
            # utf-8-sig: Excel and Goodreads both read the BOM correctly, and
            # accented authors survive the round trip
            with io.open(path, 'w', encoding='utf-8-sig', newline='') as f:
                written = exporter.write_csv(f, rows)
        except OSError as err:
            error_dialog(self.gui, PLUGIN_NAME, 'Could not write the file.',
                         det_msg=str(err), show=True)
            return

        message = ('%d book(s) written to\n%s\n\nImport it at '
                   'goodreads.com/review/import' % (written, path))
        if skipped:
            message += '\n\n%d book(s) were left out.' % len(skipped)
        info_dialog(self.gui, PLUGIN_NAME, message,
                    det_msg='\n'.join('%s - %s' % s for s in skipped)
                    if skipped else None, show=True)
