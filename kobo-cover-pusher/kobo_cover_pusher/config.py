#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Persistent settings and the configuration dialog."""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

from calibre.utils.config import JSONConfig
from qt.core import (QCheckBox, QFormLayout, QGroupBox, QLabel, Qt, QVBoxLayout,
                     QWidget)

STORE_NAME = 'plugins/kobo_cover_pusher'

DEFAULTS = {
    'use_driver_settings': True,
    'keep_aspect': True,
    'grayscale': False,
    'png': False,
    'dithered': False,
    'letterbox': False,
    'letterbox_color': '#000000',
    'match_by_uuid_only': False,
    'confirm_over': 20,
}

prefs = JSONConfig(STORE_NAME)
prefs.defaults.update(copy.deepcopy(DEFAULTS))


def get_settings():
    out = copy.deepcopy(DEFAULTS)
    for key in DEFAULTS:
        if key in prefs:
            out[key] = prefs[key]
    return out


def save_settings(settings):
    for key, value in settings.items():
        if key in DEFAULTS:
            prefs[key] = value


def form_layout(parent):
    layout = QFormLayout(parent)
    layout.setFieldGrowthPolicy(
        QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
    return layout


class ConfigWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.settings = get_settings()
        outer = QVBoxLayout(self)

        self.use_driver = QCheckBox(
            "Use the Kobo driver's own cover settings", self)
        self.use_driver.setToolTip(
            'Preferences -> Plugins -> Device interface -> KoboTouch. '
            'Uncheck to decide here instead.')
        self.use_driver.toggled.connect(self._sync_enabled)
        outer.addWidget(self.use_driver)

        box = QGroupBox('Cover options used when the box above is unchecked',
                        self)
        form = form_layout(box)
        self.keep_aspect = QCheckBox('Keep the cover aspect ratio', box)
        self.grayscale = QCheckBox('Convert to greyscale', box)
        self.png = QCheckBox('Write PNG thumbnails', box)
        self.dithered = QCheckBox('Dither (older e-ink screens)', box)
        self.letterbox = QCheckBox('Letterbox full screen covers', box)
        for widget in (self.keep_aspect, self.grayscale, self.png,
                       self.dithered, self.letterbox):
            form.addRow('', widget)
        outer.addWidget(box)
        self.box = box

        self.uuid_only = QCheckBox(
            'Only match books by their calibre identifier, never by title',
            self)
        self.uuid_only.setToolTip(
            'Safest, but it skips books that were copied to the Kobo by any '
            'other means than calibre.')
        outer.addWidget(self.uuid_only)

        note = QLabel(
            'Covers are written straight into the device thumbnail cache. The '
            'book files are never resent, so your reading position, bookmarks '
            'and annotations are untouched.', self)
        note.setWordWrap(True)
        outer.addWidget(note)
        outer.addStretch(1)
        self._load()

    def _sync_enabled(self, *args):
        self.box.setEnabled(not self.use_driver.isChecked())

    def _load(self):
        s = self.settings
        self.use_driver.setChecked(bool(s.get('use_driver_settings', True)))
        self.keep_aspect.setChecked(bool(s.get('keep_aspect', True)))
        self.grayscale.setChecked(bool(s.get('grayscale', False)))
        self.png.setChecked(bool(s.get('png', False)))
        self.dithered.setChecked(bool(s.get('dithered', False)))
        self.letterbox.setChecked(bool(s.get('letterbox', False)))
        self.uuid_only.setChecked(bool(s.get('match_by_uuid_only', False)))
        self._sync_enabled()

    def _collect(self):
        out = dict(self.settings)
        out.update({
            'use_driver_settings': self.use_driver.isChecked(),
            'keep_aspect': self.keep_aspect.isChecked(),
            'grayscale': self.grayscale.isChecked(),
            'png': self.png.isChecked(),
            'dithered': self.dithered.isChecked(),
            'letterbox': self.letterbox.isChecked(),
            'match_by_uuid_only': self.uuid_only.isChecked(),
        })
        return out

    def save_settings(self):
        self.settings = self._collect()
        save_settings(self.settings)
