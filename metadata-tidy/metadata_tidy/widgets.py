#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The preview window: every proposed change, book by book, before anything is
written to the library.  Rows can be unticked, and the proposed series,
number and title can be corrected by hand.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from qt.core import (QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout,
                     QHeaderView, QLabel, QPushButton, QTableWidget,
                     QTableWidgetItem, Qt, QVBoxLayout)

from .parser import format_index, parse_number

COLUMNS = ['Book', 'New title', 'Series', '#', 'Authors']
COL_BOOK, COL_TITLE, COL_SERIES, COL_INDEX, COL_AUTHORS = range(5)


class TidyPreviewDialog(QDialog):
    """Shows the proposals; on accept, read back ``selected_proposals()``."""

    def __init__(self, parent, proposals, total_books):
        QDialog.__init__(self, parent)
        self.proposals = proposals
        self.total_books = total_books
        self.setWindowTitle('Metadata Tidy - preview')
        self._build_ui()
        self._fill()
        self.resize(1000, min(700, 220 + 26 * max(4, len(proposals))))

    # -- construction ------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        self.summary = QLabel('', self)
        self.summary.setWordWrap(True)
        outer.addWidget(self.summary)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_BOOK, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SERIES, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_INDEX,
                                    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_AUTHORS,
                                    QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self._item_changed)
        outer.addWidget(self.table, 1)

        row = QHBoxLayout()
        for label, slot in (('Select all', lambda: self._set_all(True)),
                            ('Select none', lambda: self._set_all(False)),
                            ('Invert', self._invert)):
            button = QPushButton(label, self)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        self.count_label = QLabel('', self)
        row.addWidget(self.count_label)
        outer.addLayout(row)

        buttons = QDialogButtonBox(self)
        self.apply_button = buttons.addButton(
            'Apply', QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_button.clicked.connect(self.accept)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        outer.addWidget(buttons)

    # -- filling -----------------------------------------------------------
    def _fill(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.proposals))
        for row, proposal in enumerate(self.proposals):
            book = QTableWidgetItem(proposal.old_title)
            book.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                          Qt.ItemFlag.ItemIsEnabled |
                          Qt.ItemFlag.ItemIsSelectable)
            book.setCheckState(Qt.CheckState.Checked if proposal.selected
                               else Qt.CheckState.Unchecked)
            book.setToolTip('Matched by rule: %s' % (proposal.rule or 'none'))
            self.table.setItem(row, COL_BOOK, book)

            for column, value in ((COL_TITLE, proposal.new_title),
                                  (COL_SERIES, proposal.new_series),
                                  (COL_INDEX, format_index(proposal.new_index)),
                                  (COL_AUTHORS, proposal.new_authors)):
                item = QTableWidgetItem(value)
                if column == COL_AUTHORS and \
                        proposal.new_authors == proposal.old_authors:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled |
                                  Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, column, item)
        self.table.blockSignals(False)
        self._refresh_counts()

    def _refresh_counts(self):
        selected = sum(1 for p in self.proposals if p.selected)
        self.count_label.setText('%d of %d selected' % (selected,
                                                        len(self.proposals)))
        self.apply_button.setEnabled(selected > 0)
        self.summary.setText(
            '%d of the %d selected book(s) carry a series in their title. '
            'Untick a row to leave that book alone; the title, series and '
            'number cells are editable if a guess needs fixing.'
            % (len(self.proposals), self.total_books))

    # -- interaction -------------------------------------------------------
    def _item_changed(self, item):
        row = item.row()
        if row >= len(self.proposals):
            return
        proposal = self.proposals[row]
        column = item.column()
        if column == COL_BOOK:
            proposal.selected = item.checkState() == Qt.CheckState.Checked
            self._refresh_counts()
        elif column == COL_TITLE:
            proposal.new_title = item.text().strip()
        elif column == COL_SERIES:
            proposal.new_series = item.text().strip()
        elif column == COL_INDEX:
            value = parse_number(item.text())
            proposal.new_index = value
            self.table.blockSignals(True)
            item.setText(format_index(value))
            self.table.blockSignals(False)
        elif column == COL_AUTHORS:
            proposal.new_authors = item.text().strip()

    def _set_all(self, state):
        self.table.blockSignals(True)
        for row, proposal in enumerate(self.proposals):
            proposal.selected = state
            self.table.item(row, COL_BOOK).setCheckState(
                Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._refresh_counts()

    def _invert(self):
        self.table.blockSignals(True)
        for row, proposal in enumerate(self.proposals):
            proposal.selected = not proposal.selected
            self.table.item(row, COL_BOOK).setCheckState(
                Qt.CheckState.Checked if proposal.selected
                else Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._refresh_counts()

    def selected_proposals(self):
        return [p for p in self.proposals if p.selected and p.changed]
