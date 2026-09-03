#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Persistent settings and the configuration dialog."""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

from calibre.utils.config import JSONConfig
from qt.core import (QCheckBox, QComboBox, QFormLayout, QLabel, QLineEdit,
                     QSpinBox, Qt, QVBoxLayout, QWidget)

from .exporter import EXCLUSIVE_SHELVES

STORE_NAME = 'plugins/goodreads_export'

DEFAULTS = {
    'default_shelf': 'to-read',
    'read_column': '',
    'date_read_column': '',
    'original_year_column': '',
    'shelf_from_tags': True,
    'max_shelves': 12,
    'include_review': False,
    'review_limit': 0,
    'only_with_isbn': False,
    'binding': '',
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


NOTE = ("Goodreads keeps one exclusive shelf per book - read, "
        "currently-reading or to-read - plus any number of ordinary shelves. "
        "A tag spelled like one of the three decides the exclusive shelf; the "
        "column below wins over it when it is filled in.")

COLUMN_NOTE = ("Custom columns, with their leading #. Leave empty when you "
               "have none: the export still works, those cells are simply "
               "left blank.")


class ConfigWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.settings = get_settings()
        outer = QVBoxLayout(self)
        form = form_layout(self)
        outer.addLayout(form)

        self.default_shelf = QComboBox(self)
        for shelf in ('',) + EXCLUSIVE_SHELVES:
            self.default_shelf.addItem(shelf or '(none)', shelf)
        form.addRow('Shelf when nothing says otherwise:', self.default_shelf)

        self.read_column = QLineEdit(self)
        self.read_column.setPlaceholderText('#read')
        form.addRow('Read status column:', self.read_column)

        self.date_read_column = QLineEdit(self)
        self.date_read_column.setPlaceholderText('#date_read')
        form.addRow('Date read column:', self.date_read_column)

        self.original_year_column = QLineEdit(self)
        self.original_year_column.setPlaceholderText('#original_year')
        form.addRow('Original publication year:', self.original_year_column)

        note = QLabel(COLUMN_NOTE, self)
        note.setWordWrap(True)
        form.addRow('', note)

        self.shelf_from_tags = QCheckBox('Turn tags into shelves', self)
        form.addRow('', self.shelf_from_tags)

        self.max_shelves = QSpinBox(self)
        self.max_shelves.setRange(1, 50)
        form.addRow('Maximum shelves per book:', self.max_shelves)

        self.binding = QLineEdit(self)
        self.binding.setPlaceholderText('Paperback, Kindle Edition, ...')
        form.addRow('Binding:', self.binding)

        self.include_review = QCheckBox(
            'Export the comments as your review', self)
        form.addRow('', self.include_review)

        self.review_limit = QSpinBox(self)
        self.review_limit.setRange(0, 20000)
        self.review_limit.setSingleStep(500)
        self.review_limit.setSpecialValueText('No limit')
        form.addRow('Trim reviews to:', self.review_limit)

        self.only_with_isbn = QCheckBox(
            'Skip books that have no ISBN', self)
        self.only_with_isbn.setToolTip(
            'Goodreads matches best on ISBN. Without one it falls back to '
            'title and author, which is where webnovels and fan translations '
            'usually fail.')
        form.addRow('', self.only_with_isbn)

        shelf_note = QLabel(NOTE, self)
        shelf_note.setWordWrap(True)
        outer.addWidget(shelf_note)
        outer.addStretch(1)
        self._load()

    def _load(self):
        s = self.settings
        index = self.default_shelf.findData(s.get('default_shelf', 'to-read'))
        self.default_shelf.setCurrentIndex(max(0, index))
        self.read_column.setText(s.get('read_column', ''))
        self.date_read_column.setText(s.get('date_read_column', ''))
        self.original_year_column.setText(s.get('original_year_column', ''))
        self.shelf_from_tags.setChecked(bool(s.get('shelf_from_tags', True)))
        self.max_shelves.setValue(int(s.get('max_shelves', 12)))
        self.binding.setText(s.get('binding', ''))
        self.include_review.setChecked(bool(s.get('include_review')))
        self.review_limit.setValue(int(s.get('review_limit', 0)))
        self.only_with_isbn.setChecked(bool(s.get('only_with_isbn')))

    def _collect(self):
        data = self.default_shelf.currentData()
        return {
            'default_shelf': '' if data is None else data,
            'read_column': self.read_column.text().strip(),
            'date_read_column': self.date_read_column.text().strip(),
            'original_year_column': self.original_year_column.text().strip(),
            'shelf_from_tags': self.shelf_from_tags.isChecked(),
            'max_shelves': self.max_shelves.value(),
            'binding': self.binding.text().strip(),
            'include_review': self.include_review.isChecked(),
            'review_limit': self.review_limit.value(),
            'only_with_isbn': self.only_with_isbn.isChecked(),
        }

    def save_settings(self):
        self.settings = self._collect()
        save_settings(self.settings)
