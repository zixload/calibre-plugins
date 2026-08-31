#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Persistent settings and the configuration dialog.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

from calibre.utils.config import JSONConfig
from qt.core import (QCheckBox, QFormLayout, QLabel, QVBoxLayout, QWidget, Qt)

STORE_NAME = 'plugins/metadata_tidy'

DEFAULTS = {
    'rewrite_title': True,
    'fill_empty_series_only': True,
    'allow_bare_number': False,
    'swap_authors': False,
    'normalise_spaces': True,
    'backup_enabled': True,
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
        form = form_layout(self)
        outer.addLayout(form)

        self.rewrite = QCheckBox(
            'Rewrite the title once the series is extracted', self)
        self.rewrite.setToolTip(
            '"La Guerre du pavot, Livre 2 : La Republique du Dragon" becomes '
            'the title "La Republique du Dragon" in the series "La Guerre du '
            'pavot". Uncheck to fill the series but leave titles untouched.')
        form.addRow('', self.rewrite)

        self.empty_only = QCheckBox(
            'Never overwrite a series that is already filled in', self)
        form.addRow('', self.empty_only)

        self.bare = QCheckBox(
            'Also treat a bare trailing number as a volume number', self)
        self.bare.setToolTip(
            'Off by default: "Fahrenheit 451" and "Catch 22" are not '
            'volume 451 and 22 of anything.')
        form.addRow('', self.bare)

        self.swap = QCheckBox('Swap author names written "Last, First"', self)
        form.addRow('', self.swap)

        self.spaces = QCheckBox(
            'Normalise whitespace and spacing around punctuation', self)
        form.addRow('', self.spaces)

        self.backup = QCheckBox(
            'Remember the previous values so the change can be undone', self)
        form.addRow('', self.backup)

        note = QLabel(
            'Nothing is ever applied without the preview window: every book '
            'is listed with its proposed title, series and number, and each '
            'row can be unticked or edited by hand.', self)
        note.setWordWrap(True)
        outer.addWidget(note)
        outer.addStretch(1)
        self._load()

    def _load(self):
        s = self.settings
        self.rewrite.setChecked(bool(s.get('rewrite_title', True)))
        self.empty_only.setChecked(bool(s.get('fill_empty_series_only', True)))
        self.bare.setChecked(bool(s.get('allow_bare_number', False)))
        self.swap.setChecked(bool(s.get('swap_authors', False)))
        self.spaces.setChecked(bool(s.get('normalise_spaces', True)))
        self.backup.setChecked(bool(s.get('backup_enabled', True)))

    def _collect(self):
        return {
            'rewrite_title': self.rewrite.isChecked(),
            'fill_empty_series_only': self.empty_only.isChecked(),
            'allow_bare_number': self.bare.isChecked(),
            'swap_authors': self.swap.isChecked(),
            'normalise_spaces': self.spaces.isChecked(),
            'backup_enabled': self.backup.isChecked(),
        }

    def save_settings(self):
        self.settings = self._collect()
        save_settings(self.settings)
