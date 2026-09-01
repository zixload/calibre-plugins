#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reusable Qt widgets and the preview dialog.

This module owns the GUI only: it never touches the calibre database.  The
caller hands it a list of entries (book id, BookInfo, artwork) and gets back
the entries the user validated.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import io
import os

from qt.core import (QApplication, QCheckBox, QComboBox, QDialog,
                     QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
                     QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPixmap,
                     QPushButton, QScrollArea, QSize, QSizePolicy, QSlider,
                     QSpinBox, Qt, QTimer, QToolButton, QVBoxLayout, QWidget)

from . import badges as badges_mod
from . import presets as presets_mod
from .generator import merged_settings, render_cover, stamp_badge

IMAGE_FILTER = 'Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)'
FONT_FILTER = 'Fonts (*.ttf *.otf *.ttc *.otc)'


def pil_to_pixmap(img):
    """Convert a PIL image to a QPixmap without touching the filesystem."""
    buf = io.BytesIO()
    img.convert('RGB').save(buf, 'PNG')
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue(), 'PNG')
    return pixmap


# --------------------------------------------------------------------------
# Small reusable widgets
# --------------------------------------------------------------------------

class FilePicker(QWidget):
    """Line edit + Browse + Clear, used for fonts and background images."""

    def __init__(self, parent=None, caption='Choose a file',
                 file_filter='All files (*)', placeholder='Automatic'):
        QWidget.__init__(self, parent)
        self.caption = caption
        self.file_filter = file_filter
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        layout.addWidget(self.edit, 1)
        browse = QToolButton(self)
        browse.setText('...')
        browse.setToolTip('Browse')
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

    def _browse(self):
        start = self.edit.text().strip() or os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(self, self.caption, start,
                                              self.file_filter)
        if path:
            self.edit.setText(path)

    def value(self):
        return self.edit.text().strip()

    def set_value(self, text):
        self.edit.setText(text or '')


class DirPicker(FilePicker):
    def _browse(self):
        start = self.edit.text().strip() or os.path.expanduser('~')
        path = QFileDialog.getExistingDirectory(self, self.caption, start)
        if path:
            self.edit.setText(path)


class IntensitySlider(QWidget):
    """0 .. 200 % multiplier with a live label."""

    def __init__(self, parent=None, minimum=0, maximum=200, suffix='%'):
        QWidget.__init__(self, parent)
        self.suffix = suffix
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(minimum, maximum)
        self.slider.setSingleStep(5)
        self.slider.setPageStep(10)
        layout.addWidget(self.slider, 1)
        self.label = QLabel('100%', self)
        self.label.setMinimumWidth(46)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight |
                                Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.label)
        self.slider.valueChanged.connect(self._sync)

    def _sync(self, value):
        self.label.setText('%d%s' % (value, self.suffix))

    def value(self):
        return self.slider.value() / 100.0

    def set_value(self, ratio):
        self.slider.setValue(int(round(float(ratio) * 100)))
        self._sync(self.slider.value())

    @property
    def valueChanged(self):
        return self.slider.valueChanged


def form_layout(parent):
    """QFormLayout whose fields actually fill the available width.

    calibre's Qt style does not use AllNonFixedFieldsGrow by default, which
    leaves line edits stuck at their size hint.
    """
    layout = QFormLayout(parent)
    layout.setFieldGrowthPolicy(
        QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
    return layout


def combo(parent, choices, current=None):
    """QComboBox carrying (value, label) pairs in the item data."""
    box = QComboBox(parent)
    for value, label in choices:
        box.addItem(label, value)
    if current is not None:
        index = box.findData(current)
        if index >= 0:
            box.setCurrentIndex(index)
    return box


def combo_value(box, fallback=''):
    data = box.currentData()
    return fallback if data is None else data


# --------------------------------------------------------------------------
# Preview dialog
# --------------------------------------------------------------------------

PREVIEW_WIDTH = 440


class PreviewDialog(QDialog):
    """See the cover before applying it, and tweak the quick settings.

    *entries* is a list of dicts with the keys "book_id", "info" (BookInfo)
    and "image" (bytes or path, may be None).  After exec(), read back
    ``settings``, ``entries`` and ``apply_to_all``.
    """

    def __init__(self, parent, entries, settings):
        QDialog.__init__(self, parent)
        self.entries = entries
        self.settings = merged_settings(settings)
        self.index = 0
        self.apply_to_all = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(180)
        self._render_timer.timeout.connect(self.regenerate)

        self.setWindowTitle('Stylish cover - preview')
        self._build_ui()
        self._load_settings_into_ui()
        self._show_entry()

    # -- construction ------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)

        # left: the preview itself
        left = QVBoxLayout()
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_label.setMinimumSize(QSize(PREVIEW_WIDTH, int(PREVIEW_WIDTH * 1.5)))
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Fixed,
                                         QSizePolicy.Policy.Fixed)
        left.addWidget(self.preview_label)

        nav = QHBoxLayout()
        self.prev_button = QPushButton('<', self)
        self.prev_button.clicked.connect(lambda: self._step(-1))
        self.next_button = QPushButton('>', self)
        self.next_button.clicked.connect(lambda: self._step(1))
        self.counter = QLabel('', self)
        self.counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.counter, 1)
        nav.addWidget(self.next_button)
        left.addLayout(nav)
        body.addLayout(left)

        # right: the quick controls, scrollable so the dialog fits small screens
        panel = QWidget(self)
        right = QVBoxLayout(panel)
        right.setContentsMargins(0, 0, 8, 0)
        scroll = QScrollArea(self)
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(400)
        body.addWidget(scroll, 1)

        book_box = QGroupBox('Book', panel)
        form = form_layout(book_box)
        self.title_edit = QLineEdit(self)
        self.author_edit = QLineEdit(self)
        self.series_edit = QLineEdit(self)
        for widget in (self.title_edit, self.author_edit, self.series_edit):
            widget.textEdited.connect(self._schedule)
        form.addRow('Title:', self.title_edit)
        form.addRow('Author:', self.author_edit)
        form.addRow('Series:', self.series_edit)

        image_row = QHBoxLayout()
        self.image_label = QLabel('Book cover', self)
        self.image_label.setWordWrap(True)
        choose = QPushButton('Change image...', self)
        choose.clicked.connect(self._choose_image)
        reset = QPushButton('Reset', self)
        reset.clicked.connect(self._reset_image)
        image_row.addWidget(self.image_label, 1)
        image_row.addWidget(choose)
        image_row.addWidget(reset)
        form.addRow('Artwork:', self._wrap(image_row))
        right.addWidget(book_box)

        style_box = QGroupBox('Style', panel)
        sform = form_layout(style_box)
        self.preset_combo = combo(self, presets_mod.preset_choices(
            self.settings.get('user_presets')), self.settings.get('preset'))
        self.preset_combo.currentIndexChanged.connect(self._schedule)
        sform.addRow('Preset:', self.preset_combo)

        self.title_pos_combo = combo(self, [
            ('auto', 'Preset default'), ('top', 'Top'), ('upper', 'Upper third'),
            ('center', 'Centre'), ('lower', 'Lower third'), ('bottom', 'Bottom')])
        self.title_pos_combo.currentIndexChanged.connect(self._schedule)
        sform.addRow('Title position:', self.title_pos_combo)

        self.title_size = IntensitySlider(self, 40, 200)
        self.title_size.valueChanged.connect(self._schedule)
        sform.addRow('Title size:', self.title_size)

        self.author_size = IntensitySlider(self, 40, 200)
        self.author_size.valueChanged.connect(self._schedule)
        sform.addRow('Author size:', self.author_size)

        self.lines_spin = QSpinBox(self)
        self.lines_spin.setRange(0, 4)
        self.lines_spin.setSpecialValueText('Preset')
        self.lines_spin.valueChanged.connect(self._schedule)
        sform.addRow('Title lines:', self.lines_spin)
        right.addWidget(style_box)

        fx_box = QGroupBox('Effects', panel)
        fform = form_layout(fx_box)
        self.shadow_slider = IntensitySlider(self)
        self.stroke_slider = IntensitySlider(self)
        self.glow_slider = IntensitySlider(self)
        self.gradient_slider = IntensitySlider(self)
        for label, widget in (('Shadow:', self.shadow_slider),
                              ('Stroke:', self.stroke_slider),
                              ('Glow:', self.glow_slider),
                              ('Gradient:', self.gradient_slider)):
            widget.valueChanged.connect(self._schedule)
            fform.addRow(label, widget)
        self.auto_contrast = QCheckBox('Automatic contrast behind the text', self)
        self.auto_contrast.stateChanged.connect(self._schedule)
        fform.addRow('', self.auto_contrast)
        right.addWidget(fx_box)

        asian_box = QGroupBox('Asian subtitle', panel)
        aform = form_layout(asian_box)
        self.asian_check = QCheckBox('Display Asian subtitle', self)
        self.asian_check.stateChanged.connect(self._schedule)
        aform.addRow('', self.asian_check)
        self.asian_edit = QLineEdit(self)
        self.asian_edit.setPlaceholderText(
            'Never invented automatically - type it or use a custom column')
        self.asian_edit.textEdited.connect(self._schedule)
        aform.addRow('Asian title:', self.asian_edit)
        self.asian_mode = combo(self, [('auto', 'Preset default'),
                                       ('horizontal', 'Horizontal'),
                                       ('vertical', 'Vertical')])
        self.asian_mode.currentIndexChanged.connect(self._schedule)
        aform.addRow('Mode:', self.asian_mode)
        right.addWidget(asian_box)
        right.addStretch(1)

        buttons = QDialogButtonBox(self)
        self.regen_button = buttons.addButton(
            'Regenerate', QDialogButtonBox.ButtonRole.ResetRole)
        self.regen_button.clicked.connect(self.regenerate)
        self.apply_button = buttons.addButton(
            'Apply', QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_button.clicked.connect(self._apply_one)
        self.apply_all_button = buttons.addButton(
            'Apply to all', QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_all_button.clicked.connect(self._apply_all)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        self.apply_all_button.setVisible(len(self.entries) > 1)
        outer.addWidget(buttons)

    @staticmethod
    def _wrap(layout):
        holder = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        holder.setLayout(layout)
        return holder

    # -- settings <-> ui ---------------------------------------------------
    def _load_settings_into_ui(self):
        s = self.settings
        index = self.title_pos_combo.findData(s.get('title_position', 'auto'))
        self.title_pos_combo.setCurrentIndex(max(0, index))
        self.title_size.set_value(s.get('title_size_scale', 1.0))
        self.author_size.set_value(s.get('author_size_scale', 1.0))
        self.lines_spin.setValue(int(s.get('title_max_lines') or 0))
        self.shadow_slider.set_value(s.get('shadow', 1.0))
        self.stroke_slider.set_value(s.get('stroke', 1.0))
        self.glow_slider.set_value(s.get('glow', 1.0))
        self.gradient_slider.set_value(s.get('gradient', 1.0))
        self.auto_contrast.setChecked(bool(s.get('auto_contrast', True)))
        self.asian_check.setChecked(bool(s.get('asian_enabled')))
        index = self.asian_mode.findData(s.get('asian_mode', 'auto'))
        self.asian_mode.setCurrentIndex(max(0, index))

    def collect_settings(self):
        s = dict(self.settings)
        s['preset'] = combo_value(self.preset_combo, s.get('preset'))
        s['title_position'] = combo_value(self.title_pos_combo, 'auto')
        s['title_size_scale'] = self.title_size.value()
        s['author_size_scale'] = self.author_size.value()
        s['title_max_lines'] = self.lines_spin.value()
        s['shadow'] = self.shadow_slider.value()
        s['stroke'] = self.stroke_slider.value()
        s['glow'] = self.glow_slider.value()
        s['gradient'] = self.gradient_slider.value()
        s['auto_contrast'] = self.auto_contrast.isChecked()
        s['asian_enabled'] = self.asian_check.isChecked()
        s['asian_mode'] = combo_value(self.asian_mode, 'auto')
        self.settings = s
        return s

    # -- entries -----------------------------------------------------------
    def _current(self):
        return self.entries[self.index]

    def _show_entry(self):
        entry = self._current()
        info = entry['info']
        for widget, value in ((self.title_edit, info.title),
                              (self.author_edit, info.authors),
                              (self.series_edit, info.series),
                              (self.asian_edit, info.asian_title)):
            widget.blockSignals(True)
            widget.setText(value or '')
            widget.setCursorPosition(0)  # show the start, not the tail
            widget.blockSignals(False)
        self.counter.setText('%d / %d' % (self.index + 1, len(self.entries)))
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index < len(self.entries) - 1)
        custom = entry.get('custom_image')
        self.image_label.setText(os.path.basename(custom) if custom
                                 else ('Book cover' if entry.get('image')
                                       else 'No cover - gradient will be used'))
        self.regenerate()

    def _harvest_entry(self):
        entry = self._current()
        info = entry['info']
        info.title = self.title_edit.text()
        info.authors = self.author_edit.text()
        info.series = self.series_edit.text()
        info.asian_title = self.asian_edit.text()

    def _step(self, delta):
        self._harvest_entry()
        self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        self._show_entry()

    def _choose_image(self):
        start = self.settings.get('image_library') or os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self, 'Choose the artwork for this cover', start, IMAGE_FILTER)
        if path:
            self._current()['custom_image'] = path
            self.image_label.setText(os.path.basename(path))
            self.regenerate()

    def _reset_image(self):
        self._current().pop('custom_image', None)
        entry = self._current()
        self.image_label.setText('Book cover' if entry.get('image')
                                 else 'No cover - gradient will be used')
        self.regenerate()

    # -- rendering ---------------------------------------------------------
    def _schedule(self, *args):
        self._render_timer.start()

    def regenerate(self):
        self._render_timer.stop()
        self._harvest_entry()
        settings = self.collect_settings()
        entry = self._current()
        preview = dict(settings)
        ratio = float(settings.get('height', 2400)) / max(1, int(settings.get('width', 1600)))
        preview['width'] = PREVIEW_WIDTH
        preview['height'] = max(1, int(round(PREVIEW_WIDTH * ratio)))
        source = entry.get('custom_image') or entry.get('image')
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            image = render_cover(source, entry['info'], preview)
            self.preview_label.setPixmap(pil_to_pixmap(image))
            self.preview_label.setText('')
        except Exception as err:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview failed:\n%s' % err)
            import traceback
            traceback.print_exc()
        finally:
            QApplication.restoreOverrideCursor()

    # -- exit --------------------------------------------------------------
    def _apply_one(self):
        self._harvest_entry()
        self.collect_settings()
        self.apply_to_all = False
        self.accept()

    def _apply_all(self):
        self._harvest_entry()
        self.collect_settings()
        self.apply_to_all = True
        self.accept()

    def selected_entries(self):
        return self.entries if self.apply_to_all else [self._current()]


class BadgePreviewDialog(QDialog):
    """See the badge on the real covers before stamping anything.

    Unlike PreviewDialog this never regenerates the artwork: it draws the
    badge onto the cover exactly as it is, which is what the menu entry does.
    """

    def __init__(self, parent, entries, settings):
        QDialog.__init__(self, parent)
        self.entries = entries
        self.settings = merged_settings(settings)
        self.settings['badge_enabled'] = True
        self.index = 0
        self.apply_to_all = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self.regenerate)

        self.setWindowTitle('Stylish covers - badge preview')
        self._build_ui()
        self._load_settings_into_ui()
        self._show_entry()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)

        left = QVBoxLayout()
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_label.setMinimumSize(QSize(PREVIEW_WIDTH,
                                                int(PREVIEW_WIDTH * 1.5)))
        left.addWidget(self.preview_label)
        nav = QHBoxLayout()
        self.prev_button = QPushButton('<', self)
        self.prev_button.clicked.connect(lambda: self._step(-1))
        self.next_button = QPushButton('>', self)
        self.next_button.clicked.connect(lambda: self._step(1))
        self.counter = QLabel('', self)
        self.counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.counter, 1)
        nav.addWidget(self.next_button)
        left.addLayout(nav)
        body.addLayout(left)

        panel = QWidget(self)
        right = QVBoxLayout(panel)
        scroll = QScrollArea(self)
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(360)
        body.addWidget(scroll, 1)

        box = QGroupBox('Badge', panel)
        form = form_layout(box)
        self.badge_combo = combo(box, badges_mod.badge_choices(
            self.settings.get('user_badges')), self.settings.get('badge_preset'))
        self.badge_combo.currentIndexChanged.connect(self._schedule)
        form.addRow('Badge:', self.badge_combo)

        self.text_edit = QLineEdit(box)
        self.text_edit.textEdited.connect(self._schedule)
        form.addRow('Text:', self.text_edit)

        self.side_combo = combo(box, [
            ('auto', 'Automatic - the quietest side'),
            ('left', 'Left margin'), ('right', 'Right margin'),
            ('tl', 'Top left corner'), ('tr', 'Top right corner'),
            ('bl', 'Bottom left corner'), ('br', 'Bottom right corner')])
        self.side_combo.currentIndexChanged.connect(self._schedule)
        form.addRow('Position:', self.side_combo)

        self.size_slider = IntensitySlider(box, 40, 200)
        self.size_slider.valueChanged.connect(self._schedule)
        form.addRow('Size:', self.size_slider)
        self.opacity_slider = IntensitySlider(box, 20, 100)
        self.opacity_slider.valueChanged.connect(self._schedule)
        form.addRow('Opacity:', self.opacity_slider)

        self.flowers_check = QCheckBox('Draw the flowers', box)
        self.flowers_check.stateChanged.connect(self._schedule)
        form.addRow('', self.flowers_check)
        self.scrim_check = QCheckBox('Darken behind the badge', box)
        self.scrim_check.stateChanged.connect(self._schedule)
        form.addRow('', self.scrim_check)
        right.addWidget(box)

        note = QLabel(
            'The artwork is not regenerated: the badge is drawn onto the '
            'cover as it is. The previous cover is backed up, so Restore '
            'previous cover undoes this.', panel)
        note.setWordWrap(True)
        right.addWidget(note)
        right.addStretch(1)

        buttons = QDialogButtonBox(self)
        self.apply_button = buttons.addButton(
            'Apply', QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_button.clicked.connect(self._apply_one)
        self.apply_all_button = buttons.addButton(
            'Apply to all', QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_all_button.clicked.connect(self._apply_all)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        self.apply_all_button.setVisible(len(self.entries) > 1)
        outer.addWidget(buttons)

    def _load_settings_into_ui(self):
        s = self.settings
        self.text_edit.setText(s.get('badge_text', ''))
        index = self.side_combo.findData(s.get('badge_side', 'auto'))
        self.side_combo.setCurrentIndex(max(0, index))
        self.size_slider.set_value(s.get('badge_size_scale', 1.0))
        self.opacity_slider.set_value(s.get('badge_opacity', 1.0))
        self.flowers_check.setChecked(bool(s.get('badge_ornament', True)))
        self.scrim_check.setChecked(bool(s.get('badge_scrim', True)))

    def collect_settings(self):
        s = dict(self.settings)
        s['badge_enabled'] = True
        s['badge_preset'] = combo_value(self.badge_combo,
                                        badges_mod.DEFAULT_BADGE)
        s['badge_text'] = self.text_edit.text()
        s['badge_side'] = combo_value(self.side_combo, 'auto')
        s['badge_size_scale'] = self.size_slider.value()
        s['badge_opacity'] = self.opacity_slider.value()
        s['badge_ornament'] = self.flowers_check.isChecked()
        s['badge_scrim'] = self.scrim_check.isChecked()
        self.settings = s
        return s

    def _current(self):
        return self.entries[self.index]

    def _show_entry(self):
        self.counter.setText('%d / %d' % (self.index + 1, len(self.entries)))
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index < len(self.entries) - 1)
        self.regenerate()

    def _step(self, delta):
        self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        self._show_entry()

    def _schedule(self, *args):
        self._timer.start()

    def regenerate(self):
        self._timer.stop()
        settings = self.collect_settings()
        entry = self._current()
        if not entry.get('image'):
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('This book has no cover to stamp.')
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            from PIL import Image
            from . import imageops
            source = imageops.load_image(entry['image'])
            width = PREVIEW_WIDTH
            height = max(1, int(source.height * width / float(source.width)))
            small = source.resize((width, height), imageops.RESAMPLE_LANCZOS)
            self.preview_label.setPixmap(
                pil_to_pixmap(stamp_badge(small, settings)))
            self.preview_label.setText('')
        except Exception as err:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview failed:\n%s' % err)
            import traceback
            traceback.print_exc()
        finally:
            QApplication.restoreOverrideCursor()

    def _apply_one(self):
        self.collect_settings()
        self.apply_to_all = False
        self.accept()

    def _apply_all(self):
        self.collect_settings()
        self.apply_to_all = True
        self.accept()

    def selected_entries(self):
        return self.entries if self.apply_to_all else [self._current()]
