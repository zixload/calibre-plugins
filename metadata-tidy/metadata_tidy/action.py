#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The calibre side: toolbar button, menu, reading the selection, writing the
accepted changes back and undoing them.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import traceback

from calibre.gui2 import error_dialog, info_dialog, question_dialog
from calibre.gui2.actions import InterfaceAction
from qt.core import QIcon, QMenu, QToolButton

from . import backup
from .config import get_settings
from . import tidy
from .widgets import TidyPreviewDialog

PLUGIN_NAME = 'Metadata Tidy'
PLUGIN_ICON = 'images/icon.png'
ORIGINAL_TITLE_COLUMN = 'original_title'


def _load_icon():
    try:
        return get_icons(PLUGIN_ICON, PLUGIN_NAME)  # noqa: F821 (calibre builtin)
    except Exception:
        return QIcon.ic('edit_input.png') if hasattr(QIcon, 'ic') else QIcon()


class MetadataTidyAction(InterfaceAction):

    name = PLUGIN_NAME
    action_spec = ('Metadata Tidy', None,
                   'Extract the series and volume number from book titles', ())
    action_type = 'current'
    popup_type = QToolButton.ToolButtonPopupMode.MenuButtonPopup
    dont_add_to = frozenset(['context-menu-device'])

    # -- lifecycle ---------------------------------------------------------
    def genesis(self):
        icon = _load_icon()
        self.qaction.setIcon(icon)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.qaction.triggered.connect(self.tidy_selected)

        m = self.menu
        self.create_menu_action(
            m, 'mdt_tidy', 'Tidy selected books...', icon=icon,
            description='Preview and apply series, title and author fixes',
            triggered=self.tidy_selected)
        m.addSeparator()
        self.create_menu_action(
            m, 'mdt_undo', 'Undo last tidy',
            description='Put back the values replaced by the last run',
            triggered=self.undo_last)
        m.addSeparator()
        self.create_menu_action(
            m, 'mdt_column', 'Create the #original_title column...',
            description='A text column for the original chinese, korean or '
                        'japanese title, used by Stylish Cover Generator',
            triggered=self.create_original_title_column)
        self.create_menu_action(
            m, 'mdt_settings', 'Settings...',
            description='Which fixes are proposed',
            triggered=self.show_settings)

    def location_selected(self, loc):
        self.qaction.setEnabled(loc == 'library')

    def show_settings(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    # -- helpers -----------------------------------------------------------
    def _db(self):
        return self.gui.current_db.new_api

    def _library_id(self):
        try:
            return self.gui.current_db.library_id
        except Exception:
            return 'library'

    def selected_ids(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, PLUGIN_NAME,
                         'Select at least one book first.', show=True)
            return []
        model = self.gui.library_view.model()
        return [model.id(row) for row in rows]

    def _refresh(self, book_ids):
        try:
            self.gui.library_view.model().refresh_ids(
                book_ids, current_row=self.gui.library_view.currentIndex().row())
        except Exception:
            self.gui.library_view.model().refresh_ids(book_ids)
        try:
            self.gui.tags_view.recount()
        except Exception:
            pass

    # -- actions -----------------------------------------------------------
    def tidy_selected(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        settings = get_settings()
        db = self._db()
        proposals = tidy.build_proposals(db, book_ids, settings)
        if not proposals:
            info_dialog(
                self.gui, PLUGIN_NAME,
                'Nothing to change: none of the %d selected book(s) carry a '
                'series or a volume number in their title.' % len(book_ids),
                show=True)
            return

        dialog = TidyPreviewDialog(self.gui, proposals, len(book_ids))
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        accepted = dialog.selected_proposals()
        if accepted:
            self.apply(accepted, settings)

    def apply(self, proposals, settings):
        db = self._db()
        try:
            undo = tidy.write_changes(db, proposals)
        except Exception as err:
            traceback.print_exc()
            error_dialog(self.gui, PLUGIN_NAME, 'Could not write the changes.',
                         det_msg=str(err), show=True)
            return

        if settings.get('backup_enabled', True):
            backup.store(self._library_id(), undo)

        book_ids = [p.book_id for p in proposals]
        self._refresh(book_ids)
        self.gui.status_bar.show_message(
            '%d book(s) tidied - use Undo last tidy to revert' % len(book_ids),
            5000)

    def undo_last(self, *args):
        library_id = self._library_id()
        entries, when = backup.load(library_id)
        if not entries:
            error_dialog(self.gui, PLUGIN_NAME,
                         'No tidy has been recorded for this library.',
                         show=True)
            return
        if not question_dialog(
                self.gui, PLUGIN_NAME,
                'Put back the previous title, series and author of %d book(s), '
                'as they were %s?' % (len(entries), backup.describe_age(when))):
            return

        db = self._db()
        try:
            restored = tidy.restore(db, entries)
        except Exception as err:
            traceback.print_exc()
            error_dialog(self.gui, PLUGIN_NAME, 'Could not restore.',
                         det_msg=str(err), show=True)
            return
        if not restored:
            error_dialog(self.gui, PLUGIN_NAME,
                         'None of those books are in this library any more.',
                         show=True)
            return
        backup.clear(library_id)
        self._refresh(restored)
        self.gui.status_bar.show_message('%d book(s) restored' % len(restored),
                                         5000)

    def create_original_title_column(self, *args):
        db = self._db()
        label = ORIGINAL_TITLE_COLUMN
        if ('#' + label) in db.field_metadata:
            info_dialog(self.gui, PLUGIN_NAME,
                        'The #%s column already exists in this library.'
                        % label, show=True)
            return
        if not question_dialog(
                self.gui, PLUGIN_NAME,
                'Create the custom column #%s (text)?\n\nIt holds the original '
                'chinese, korean or japanese title, and is what Stylish Cover '
                'Generator reads for its Asian subtitle.\n\ncalibre must be '
                'restarted for a new column to appear.' % label):
            return
        try:
            db.create_custom_column(label, 'Original title', 'text', False)
        except Exception as err:
            traceback.print_exc()
            error_dialog(self.gui, PLUGIN_NAME,
                         'Could not create the column.', det_msg=str(err),
                         show=True)
            return
        info_dialog(self.gui, PLUGIN_NAME,
                    'Column #%s created. Restart calibre to see it.' % label,
                    show=True)
