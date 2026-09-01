#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The calibre side of the plugin: toolbar button, menu, database access and
batch orchestration.  All the drawing happens in generator.py, all the widgets
live in widgets.py; this file is the only one that talks to calibre's library.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import traceback

from calibre.ebooks.metadata import authors_to_string
from calibre.gui2 import error_dialog, info_dialog, question_dialog
from calibre.gui2.actions import InterfaceAction
from qt.core import (QApplication, QFileDialog, QIcon, QMenu, QProgressDialog,
                     Qt, QToolButton)

from . import backup
from . import kobo_push
from .config import get_settings, save_settings
from .generator import BookInfo, artwork_for, render_cover_bytes
from .kobo_matching import DeviceIndex
from .widgets import IMAGE_FILTER, PreviewDialog

PLUGIN_NAME = 'Stylish Covers'
PLUGIN_ICON = 'images/icon.png'


def _load_icon():
    """Plugin icon, with a graceful fallback if the resource is missing."""
    try:
        return get_icons(PLUGIN_ICON, PLUGIN_NAME)  # noqa: F821 (calibre builtin)
    except Exception:
        return QIcon.ic('default_cover.png') if hasattr(QIcon, 'ic') else QIcon()


def _swap_author(name):
    """"Sanderson, Brandon" -> "Brandon Sanderson"."""
    if ',' not in name:
        return name
    last, _sep, first = name.partition(',')
    return ('%s %s' % (first.strip(), last.strip())).strip()


class StylishCoversAction(InterfaceAction):

    name = PLUGIN_NAME
    action_spec = (
        'Stylish Covers', None,
        'Generate a stylish cover from the existing artwork and the metadata',
        ())
    action_type = 'current'
    popup_type = QToolButton.ToolButtonPopupMode.MenuButtonPopup
    dont_add_to = frozenset(['context-menu-device'])

    # -- lifecycle ---------------------------------------------------------
    def genesis(self):
        icon = _load_icon()
        self.qaction.setIcon(icon)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.qaction.triggered.connect(self.preview_covers)

        m = self.menu
        self.create_menu_action(
            m, 'scg_generate', 'Generate stylish covers', icon=icon,
            description='Generate covers for every selected book using the '
                        'saved settings',
            triggered=self.generate_covers)
        self.create_menu_action(
            m, 'scg_preview', 'Preview...', icon=icon,
            description='Tweak and check the cover before applying it',
            triggered=self.preview_covers)
        self.create_menu_action(
            m, 'scg_custom_image', 'Generate from a chosen image...', icon=icon,
            description='Use any picture from your disk as the artwork',
            triggered=self.generate_from_image)
        m.addSeparator()
        self.create_menu_action(
            m, 'scg_kobo_push', 'Push covers to the Kobo',
            description='Refresh the cover thumbnails on the connected device '
                        'without resending the books',
            triggered=self.push_to_kobo)
        self.create_menu_action(
            m, 'scg_kobo_info', 'Kobo device information...',
            description='Model, paths and the thumbnail sizes it expects',
            triggered=self.show_device_info)
        m.addSeparator()
        self.create_menu_action(
            m, 'scg_restore', 'Restore previous cover',
            description='Put back the cover that was replaced last',
            triggered=self.restore_previous)
        self.create_menu_action(
            m, 'scg_restore_original', 'Restore original cover',
            description='Put back the cover the book had before this plugin '
                        'ever touched it',
            triggered=self.restore_original)
        m.addSeparator()
        self.create_menu_action(
            m, 'scg_settings', 'Settings...',
            description='Presets, fonts, effects and output size',
            triggered=self.show_settings)

    def location_selected(self, loc):
        self.qaction.setEnabled(loc == 'library')

    def show_settings(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def apply_settings(self):
        # settings are read fresh on every run, nothing to cache here
        pass

    # -- database helpers --------------------------------------------------
    def _db(self):
        return self.gui.current_db.new_api

    def _library_id(self):
        try:
            return self.gui.current_db.library_id
        except Exception:
            return 'library'

    def selected_ids(self, message='Select at least one book first.'):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, PLUGIN_NAME, message, show=True)
            return []
        model = self.gui.library_view.model()
        return [model.id(row) for row in rows]

    def _eval_template(self, template, mi):
        if not template:
            return ''
        try:
            from calibre.ebooks.metadata.book.formatter import SafeFormat
            value = SafeFormat().safe_format(template, mi, 'SCG template error',
                                             mi)
            return '' if value.startswith('SCG template error') else value
        except Exception:
            return ''

    def build_entry(self, db, book_id, settings):
        """Read one book and return the preview/generation entry for it."""
        mi = db.get_metadata(book_id)

        title = self._eval_template(settings.get('title_template'), mi) or \
            (mi.title or '')
        authors = self._eval_template(settings.get('author_template'), mi)
        if not authors:
            names = list(mi.authors or [])
            if settings.get('author_swap'):
                names = [_swap_author(n) for n in names]
            authors = authors_to_string(names) if names else ''

        asian = ''
        if settings.get('asian_enabled'):
            if settings.get('asian_source', 'column') == 'column':
                column = (settings.get('asian_column') or '').strip()
                if column:
                    try:
                        value = mi.get(column, None)
                    except Exception:
                        value = None
                    if isinstance(value, (list, tuple)):
                        value = ', '.join(str(v) for v in value)
                    asian = str(value) if value else ''
            else:
                asian = settings.get('asian_text') or ''

        info = BookInfo(title=title, authors=authors, series=mi.series or '',
                        series_index=mi.series_index, asian_title=asian)
        try:
            cover = db.cover(book_id)
        except Exception:
            cover = None
        # the illustration this cover was composed from, when the user chose
        # one: the current cover cannot serve, it already carries a title
        artwork = backup.load(self._library_id(), book_id, 'art') or None
        return {'book_id': book_id, 'info': info, 'image': cover,
                'artwork': artwork}

    # -- actions -----------------------------------------------------------
    def preview_covers(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        settings = get_settings()
        db = self._db()
        entries = [self.build_entry(db, book_id, settings)
                   for book_id in book_ids]
        dialog = PreviewDialog(self.gui, entries, settings)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        save_settings(dialog.settings)
        self.run_batch(dialog.selected_entries(), dialog.settings)

    def generate_covers(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        settings = get_settings()
        db = self._db()
        entries = [self.build_entry(db, book_id, settings)
                   for book_id in book_ids]
        if len(entries) > 5 and not question_dialog(
                self.gui, PLUGIN_NAME,
                'Generate a new cover for %d books? The current covers can be '
                'restored afterwards from the same menu.' % len(entries)):
            return
        self.run_batch(entries, settings)

    def generate_from_image(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        settings = get_settings()
        start = settings.get('image_library') or os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self.gui, 'Choose the artwork to use', start, IMAGE_FILTER)
        if not path:
            return
        db = self._db()
        entries = []
        for book_id in book_ids:
            entry = self.build_entry(db, book_id, settings)
            entry['custom_image'] = path
            entries.append(entry)
        dialog = PreviewDialog(self.gui, entries, settings)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        save_settings(dialog.settings)
        self.run_batch(dialog.selected_entries(), dialog.settings)

    # -- the batch itself --------------------------------------------------
    def run_batch(self, entries, settings):
        if not entries:
            return
        db = self._db()
        library_id = self._library_id()
        progress = QProgressDialog('Generating covers...', 'Cancel', 0,
                                   len(entries), self.gui)
        progress.setWindowTitle(PLUGIN_NAME)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)

        done, failures = [], []
        for i, entry in enumerate(entries):
            if progress.wasCanceled():
                break
            info = entry['info']
            progress.setValue(i)
            progress.setLabelText('%d / %d - %s'
                                  % (i + 1, len(entries), info.title or ''))
            QApplication.processEvents()
            book_id = entry['book_id']
            source = artwork_for(entry, settings)
            self._remember_artwork(library_id, book_id, entry, source)
            try:
                data = render_cover_bytes(source, info, settings)
            except Exception as err:
                traceback.print_exc()
                failures.append((info.title, str(err)))
                continue
            try:
                self._apply(db, library_id, book_id, data, settings,
                            entry.get('image'))
                done.append(book_id)
            except Exception as err:
                traceback.print_exc()
                failures.append((info.title, str(err)))
        progress.setValue(len(entries))

        if done:
            self._refresh(done)
        self._report(done, failures)

    def _remember_artwork(self, library_id, book_id, entry, source):
        """Keep the illustration a cover was composed from, when it is one.

        Only a picture the user supplied is worth keeping: the book's own
        cover already carries a title, so re-composing from it would print a
        second one.
        """
        if not entry.get('custom_image'):
            return
        try:
            if isinstance(source, str) and os.path.isfile(source):
                with open(source, 'rb') as f:
                    data = f.read()
            elif isinstance(source, (bytes, bytearray)):
                data = bytes(source)
            else:
                return
            backup.store(library_id, book_id, data, 'art')
            entry['artwork'] = data
        except Exception:
            traceback.print_exc()

    def _apply(self, db, library_id, book_id, data, settings, previous_cover):
        if settings.get('backup_covers', True):
            if not backup.has_backup(library_id, book_id, 'orig'):
                backup.store(library_id, book_id, previous_cover, 'orig')
            backup.store(library_id, book_id, previous_cover, 'prev')
        db.set_cover({book_id: data})
        column = (settings.get('mark_column') or '').strip()
        if column:
            try:
                db.set_field(column, {book_id: settings.get('mark_value') or ''})
            except Exception:
                traceback.print_exc()

    def _refresh(self, book_ids):
        try:
            self.gui.library_view.model().refresh_ids(
                book_ids, current_row=self.gui.library_view.currentIndex().row())
        except Exception:
            self.gui.library_view.model().refresh_ids(book_ids)
        try:
            self.gui.refresh_cover_browser()
        except Exception:
            pass
        self.gui.tags_view.recount()

    def _report(self, done, failures):
        if failures and not done:
            error_dialog(
                self.gui, PLUGIN_NAME,
                'No cover could be generated.',
                det_msg='\n'.join('%s: %s' % f for f in failures), show=True)
        elif failures:
            info_dialog(
                self.gui, PLUGIN_NAME,
                '%d cover(s) generated, %d failed.' % (len(done), len(failures)),
                det_msg='\n'.join('%s: %s' % f for f in failures), show=True)
        elif done:
            self.gui.status_bar.show_message(
                '%d stylish cover(s) generated' % len(done), 4000)


    # -- kobo --------------------------------------------------------------
    def _kobo_options(self, settings):
        """The Kobo settings, stripped of their prefix for kobo_push."""
        return dict((key[5:], value) for key, value in settings.items()
                    if key.startswith('kobo_'))

    def show_device_info(self, *args):
        try:
            device = kobo_push.connected_kobo(self.gui)
        except kobo_push.DeviceError as err:
            error_dialog(self.gui, PLUGIN_NAME, str(err), show=True)
            return
        info = kobo_push.device_summary(device)
        books = kobo_push.device_books(self.gui)
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
            lines.append('   %-28s %s'
                         % (ending, '%dx%d' % size if size else '?'))
        info_dialog(self.gui, PLUGIN_NAME, 'Kobo device information',
                    det_msg='\n'.join(lines), show=True)

    def push_to_kobo(self, *args):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        try:
            device = kobo_push.connected_kobo(self.gui)
        except kobo_push.DeviceError as err:
            error_dialog(self.gui, PLUGIN_NAME, str(err), show=True)
            return

        settings = get_settings()
        index = DeviceIndex(kobo_push.device_books(self.gui))
        if not len(index):
            error_dialog(
                self.gui, PLUGIN_NAME,
                'calibre does not list any book on this device yet. Open the '
                'device view once so it reads the device library, then try '
                'again.', show=True)
            return
        if len(book_ids) > 20 and not question_dialog(
                self.gui, PLUGIN_NAME,
                'Push the covers of %d books onto the Kobo? The book files are '
                'not resent, so your reading positions are safe.'
                % len(book_ids)):
            return

        db = self._db()
        options = kobo_push.driver_options(device, self._kobo_options(settings))
        uuid_only = bool(settings.get('kobo_match_by_uuid_only'))
        progress = QProgressDialog('Pushing covers...', 'Cancel', 0,
                                   len(book_ids), self.gui)
        progress.setWindowTitle(PLUGIN_NAME)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)

        done, skipped, failures = [], [], []
        for position, book_id in enumerate(book_ids):
            if progress.wasCanceled():
                break
            try:
                mi = db.get_metadata(book_id)
            except Exception:
                failures.append(('book %s' % book_id, 'unreadable metadata'))
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
                kobo_push.push_cover(device, device_book, cover, mi, options)
                done.append(mi.title or '')
            except Exception as err:
                traceback.print_exc()
                failures.append((mi.title or '', str(err)))
        progress.setValue(len(book_ids))

        details = []
        if skipped:
            details.append('Skipped:')
            details += ['   %s - %s' % (t, w) for t, w in skipped]
        if failures:
            if details:
                details.append('')
            details.append('Failed:')
            details += ['   %s - %s' % (t, w) for t, w in failures]
        detail = '\n'.join(details) if details else None
        if done and not (skipped or failures):
            info_dialog(self.gui, PLUGIN_NAME,
                        '%d cover(s) written to the Kobo.\n\nEject the device '
                        'and let it finish its library scan to see them.'
                        % len(done), show=True)
        elif done:
            info_dialog(self.gui, PLUGIN_NAME,
                        '%d cover(s) written, %d skipped, %d failed.'
                        % (len(done), len(skipped), len(failures)),
                        det_msg=detail, show=True)
        else:
            error_dialog(self.gui, PLUGIN_NAME,
                         'No cover could be written. None of the selected '
                         'books were matched with a book on the device.',
                         det_msg=detail, show=True)

    # -- restore -----------------------------------------------------------
    def restore_previous(self, *args):
        self._restore('prev', 'previous')

    def restore_original(self, *args):
        self._restore('orig', 'original')

    def _restore(self, kind, label):
        book_ids = self.selected_ids()
        if not book_ids:
            return
        db = self._db()
        library_id = self._library_id()
        restored, missing = [], 0
        for book_id in book_ids:
            data = backup.load(library_id, book_id, kind)
            if data is None:
                missing += 1
                continue
            try:
                if data:
                    db.set_cover({book_id: data})
                else:
                    db.set_cover({book_id: None})
                if kind == 'prev':
                    backup.discard(library_id, book_id, 'prev')
                restored.append(book_id)
            except Exception:
                traceback.print_exc()
                missing += 1
        if restored:
            self._refresh(restored)
            self.gui.status_bar.show_message(
                '%d %s cover(s) restored' % (len(restored), label), 4000)
        if missing and not restored:
            error_dialog(self.gui, PLUGIN_NAME,
                         'No %s cover was saved for the selected book(s).'
                         % label, show=True)
