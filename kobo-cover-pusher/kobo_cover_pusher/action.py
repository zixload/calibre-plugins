#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The calibre side: toolbar button, menu, and the push loop.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import traceback

from calibre.gui2 import error_dialog, info_dialog, question_dialog
from calibre.gui2.actions import InterfaceAction
from qt.core import (QApplication, QIcon, QMenu, QProgressDialog, Qt,
                     QToolButton)

from . import pusher
from .config import get_settings
from .matching import DeviceIndex

PLUGIN_NAME = 'Kobo Cover Pusher'
PLUGIN_ICON = 'images/icon.png'


def _load_icon():
    try:
        return get_icons(PLUGIN_ICON, PLUGIN_NAME)  # noqa: F821 calibre builtin
    except Exception:
        return QIcon.ic('devices/kindle.png') if hasattr(QIcon, 'ic') else QIcon()


class KoboCoverPusherAction(InterfaceAction):

    name = PLUGIN_NAME
    action_spec = ('Kobo Covers', None,
                   'Write the calibre covers onto the connected Kobo without '
                   'resending the books', ())
    action_type = 'current'
    popup_type = QToolButton.ToolButtonPopupMode.MenuButtonPopup
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        icon = _load_icon()
        self.qaction.setIcon(icon)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.qaction.triggered.connect(self.push_selected)

        m = self.menu
        self.create_menu_action(
            m, 'kcp_push', 'Push covers for the selected books', icon=icon,
            description='Refresh the cover thumbnails on the connected Kobo',
            triggered=self.push_selected)
        m.addSeparator()
        self.create_menu_action(
            m, 'kcp_info', 'Device information...',
            description='What calibre sees: model, paths and thumbnail sizes',
            triggered=self.show_device_info)
        self.create_menu_action(
            m, 'kcp_settings', 'Settings...',
            description='Cover options and how books are matched',
            triggered=self.show_settings)

    def location_selected(self, loc):
        self.qaction.setEnabled(loc == 'library')

    def show_settings(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    # -- helpers -----------------------------------------------------------
    def _db(self):
        return self.gui.current_db.new_api

    def selected_ids(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, PLUGIN_NAME,
                         'Select the books whose covers you want to push.',
                         show=True)
            return []
        model = self.gui.library_view.model()
        return [model.id(row) for row in rows]

    # -- actions -----------------------------------------------------------
    def show_device_info(self, *args):
        try:
            device = pusher.connected_kobo(self.gui)
        except pusher.DeviceError as err:
            error_dialog(self.gui, PLUGIN_NAME, str(err), show=True)
            return
        info = pusher.device_summary(device)
        books = pusher.device_books(self.gui)
        lines = [
            'Device: %s' % info['name'],
            'Driver: %s' % info['driver'],
            'Firmware: %s' % (info.get('firmware') or 'unknown'),
            'Main memory: %s' % (info['main_prefix'] or 'unknown'),
            'Books listed on the device: %d' % len(books),
            '',
            "Driver's own cover settings:",
            '   Upload covers when sending: %s'
            % ('on' if info['upload_covers'] else 'off'),
            '   Keep cover aspect ratio: %s'
            % ('on' if info['keep_cover_aspect'] else 'off'),
            '   PNG thumbnails: %s' % ('on' if info['png_covers'] else 'off'),
            '',
            'Thumbnails written for this model:',
        ]
        for ending, size in info['sizes']:
            lines.append('   %-28s %s' % (ending,
                                          '%dx%d' % size if size else '?'))
        info_dialog(self.gui, PLUGIN_NAME, 'Kobo device information',
                    det_msg='\n'.join(lines), show=True)

    def push_selected(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        try:
            device = pusher.connected_kobo(self.gui)
        except pusher.DeviceError as err:
            error_dialog(self.gui, PLUGIN_NAME, str(err), show=True)
            return

        settings = get_settings()
        index = DeviceIndex(pusher.device_books(self.gui))
        if not len(index):
            error_dialog(
                self.gui, PLUGIN_NAME,
                'calibre does not list any book on this device yet. Open the '
                'device view once so it reads the device library, then try '
                'again.', show=True)
            return

        limit = int(settings.get('confirm_over', 20) or 0)
        if limit and len(book_ids) > limit and not question_dialog(
                self.gui, PLUGIN_NAME,
                'Push the covers of %d books onto the Kobo? The book files '
                'are not resent, so your reading positions are safe.'
                % len(book_ids)):
            return

        self._run(device, index, book_ids, settings)

    def _run(self, device, index, book_ids, settings):
        db = self._db()
        options = pusher.driver_options(device, settings)
        uuid_only = bool(settings.get('match_by_uuid_only'))

        progress = QProgressDialog('Pushing covers...', 'Cancel', 0,
                                   len(book_ids), self.gui)
        progress.setWindowTitle(PLUGIN_NAME)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)

        done, skipped, failed = [], [], []
        for position, book_id in enumerate(book_ids):
            if progress.wasCanceled():
                break
            try:
                mi = db.get_metadata(book_id)
            except Exception:
                failed.append(('book %s' % book_id, 'unreadable metadata'))
                continue
            progress.setValue(position)
            progress.setLabelText('%d / %d - %s'
                                  % (position + 1, len(book_ids), mi.title or ''))
            QApplication.processEvents()

            device_book, how = index.find(getattr(mi, 'uuid', None), mi.title,
                                          mi.authors, uuid_only=uuid_only)
            if device_book is None:
                skipped.append((mi.title or '', how))
                continue
            try:
                cover = db.cover(book_id)
            except Exception:
                cover = None
            try:
                pusher.push_cover(device, device_book, cover, mi, options)
                done.append(mi.title or '')
            except Exception as err:
                traceback.print_exc()
                failed.append((mi.title or '', str(err)))
        progress.setValue(len(book_ids))
        self._report(done, skipped, failed)

    def _report(self, done, skipped, failed):
        details = []
        if skipped:
            details.append('Skipped:')
            details += ['   %s - %s' % (title, why) for title, why in skipped]
        if failed:
            if details:
                details.append('')
            details.append('Failed:')
            details += ['   %s - %s' % (title, why) for title, why in failed]
        detail = '\n'.join(details) if details else None

        if done and not (skipped or failed):
            info_dialog(
                self.gui, PLUGIN_NAME,
                '%d cover(s) written to the Kobo.\n\nEject the device and let '
                'it finish its library scan to see them.' % len(done),
                show=True)
        elif done:
            info_dialog(
                self.gui, PLUGIN_NAME,
                '%d cover(s) written, %d skipped, %d failed.'
                % (len(done), len(skipped), len(failed)),
                det_msg=detail, show=True)
        else:
            error_dialog(
                self.gui, PLUGIN_NAME,
                'No cover could be written. None of the selected books were '
                'matched with a book on the device.',
                det_msg=detail, show=True)
