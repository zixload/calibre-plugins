#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Persistent configuration and the settings dialog shown by
Preferences -> Plugins -> Stylish Cover Generator -> Customize plugin.

The only calibre dependency here is JSONConfig; everything the renderer needs
travels as a plain dict, so generator.py stays calibre-free.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

from calibre.utils.config import JSONConfig
from qt.core import (QCheckBox, QComboBox, QHBoxLayout,
                     QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
                     QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from . import presets as presets_mod
from .fonts import FontBook
from .generator import SETTINGS_DEFAULTS
from .widgets import (FONT_FILTER, DirPicker, FilePicker, IntensitySlider,
                      combo, combo_value, form_layout)

STORE_NAME = 'plugins/stylish_cover_generator'

prefs = JSONConfig(STORE_NAME)
prefs.defaults.update(copy.deepcopy(SETTINGS_DEFAULTS))


def get_settings():
    """Full settings dict: defaults completed by whatever the user changed."""
    out = copy.deepcopy(SETTINGS_DEFAULTS)
    for key in SETTINGS_DEFAULTS:
        if key in prefs:
            out[key] = prefs[key]
    return out


def save_settings(settings):
    for key, value in settings.items():
        if key in SETTINGS_DEFAULTS:
            prefs[key] = value


# Keys that a named style stores; the rest (fonts, output size, behaviour)
# stays global on purpose.
STYLE_KEYS = ('preset', 'title_position', 'author_position', 'title_size_scale',
              'author_size_scale', 'title_max_lines', 'title_case',
              'show_series', 'show_author', 'shadow', 'stroke', 'glow',
              'gradient', 'auto_contrast', 'asian_enabled', 'asian_mode',
              'asian_size_scale')


class ConfigWidget(QWidget):
    """Tabbed settings editor: Output, Style, Fonts, Effects, Asian, Metadata."""

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.settings = get_settings()
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._output_tab(), 'Output')
        self.tabs.addTab(self._style_tab(), 'Style')
        self.tabs.addTab(self._fonts_tab(), 'Fonts')
        self.tabs.addTab(self._effects_tab(), 'Effects')
        self.tabs.addTab(self._asian_tab(), 'Asian title')
        self.tabs.addTab(self._metadata_tab(), 'Metadata')
        self._load()

    # -- tabs --------------------------------------------------------------
    def _output_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.width_spin = QSpinBox(page)
        self.width_spin.setRange(300, 6000)
        self.width_spin.setSingleStep(100)
        self.width_spin.setSuffix(' px')
        form.addRow('Width:', self.width_spin)

        self.height_spin = QSpinBox(page)
        self.height_spin.setRange(300, 9000)
        self.height_spin.setSingleStep(100)
        self.height_spin.setSuffix(' px')
        form.addRow('Height:', self.height_spin)

        ratio_row = QHBoxLayout()
        self.ratio_label = QLabel('', page)
        lock = QPushButton('Force 2:3', page)
        lock.setToolTip('Set the height to 1.5x the width (standard book ratio)')
        lock.clicked.connect(
            lambda: self.height_spin.setValue(int(self.width_spin.value() * 1.5)))
        ratio_row.addWidget(self.ratio_label, 1)
        ratio_row.addWidget(lock)
        form.addRow('Ratio:', self._wrap(ratio_row))
        self.width_spin.valueChanged.connect(self._update_ratio)
        self.height_spin.valueChanged.connect(self._update_ratio)

        self.quality_spin = QSpinBox(page)
        self.quality_spin.setRange(50, 100)
        form.addRow('JPEG quality:', self.quality_spin)

        self.format_combo = combo(page, [('JPEG', 'JPEG (smaller)'),
                                         ('PNG', 'PNG (lossless)')])
        form.addRow('Format:', self.format_combo)

        self.backup_check = QCheckBox(
            'Keep a backup of the previous cover (enables Restore)', page)
        form.addRow('', self.backup_check)
        form.addRow('', QLabel(
            'The artwork is never distorted: it is scaled to cover the canvas '
            'and cropped.', page))
        return page

    def _style_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.preset_combo = combo(page, presets_mod.preset_choices(
            self.settings.get('user_presets')))
        self.preset_combo.currentIndexChanged.connect(self._update_preset_help)
        form.addRow('Preset:', self.preset_combo)
        self.preset_help = QLabel('', page)
        self.preset_help.setWordWrap(True)
        form.addRow('', self.preset_help)

        self.title_pos_combo = combo(page, [
            ('auto', 'Preset default'), ('top', 'Top'), ('upper', 'Upper third'),
            ('center', 'Centre'), ('lower', 'Lower third'), ('bottom', 'Bottom')])
        form.addRow('Title position:', self.title_pos_combo)

        self.author_pos_combo = combo(page, [
            ('auto', 'Preset default'), ('under_title', 'Under the title'),
            ('bottom', 'Bottom of the cover')])
        form.addRow('Author position:', self.author_pos_combo)

        self.title_size = IntensitySlider(page, 40, 200)
        form.addRow('Title size:', self.title_size)
        self.author_size = IntensitySlider(page, 40, 200)
        form.addRow('Author size:', self.author_size)

        self.lines_spin = QSpinBox(page)
        self.lines_spin.setRange(0, 4)
        self.lines_spin.setSpecialValueText('Preset default')
        form.addRow('Max title lines:', self.lines_spin)

        self.case_combo = combo(page, [('auto', 'Preset default'),
                                       ('upper', 'UPPERCASE'),
                                       ('none', 'As written')])
        form.addRow('Title case:', self.case_combo)

        self.series_check = QCheckBox('Show the series and its number', page)
        form.addRow('', self.series_check)
        self.author_check = QCheckBox('Show the author', page)
        form.addRow('', self.author_check)

        styles_row = QHBoxLayout()
        self.styles_combo = QComboBox(page)
        save = QPushButton('Save current...', page)
        save.clicked.connect(self._save_style)
        load = QPushButton('Load', page)
        load.clicked.connect(self._load_style)
        delete = QPushButton('Delete', page)
        delete.clicked.connect(self._delete_style)
        styles_row.addWidget(self.styles_combo, 1)
        for button in (save, load, delete):
            styles_row.addWidget(button)
        form.addRow('Saved styles:', self._wrap(styles_row))
        return page

    def _fonts_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.font_title = FilePicker(page, 'Choose the title font', FONT_FILTER)
        self.font_author = FilePicker(page, 'Choose the author font', FONT_FILTER)
        self.font_cjk = FilePicker(page, 'Choose the CJK font', FONT_FILTER)
        form.addRow('Title font:', self.font_title)
        form.addRow('Author font:', self.font_author)
        form.addRow('CJK font:', self.font_cjk)
        note = QLabel(
            'No font is shipped with this plugin. Leave a field empty to let '
            'the plugin pick a suitable font installed on your system. Any '
            '.ttf / .otf file works, including your own display faces.\n'
            'Fallback is automatic and per character: a glyph missing from the '
            'title font (chinese, korean, japanese) is drawn with the CJK font.',
            page)
        note.setWordWrap(True)
        form.addRow('', note)
        self.font_report = QLabel('', page)
        self.font_report.setWordWrap(True)
        form.addRow('Currently used:', self.font_report)
        refresh = QPushButton('Check fonts', page)
        refresh.clicked.connect(self._report_fonts)
        form.addRow('', refresh)
        return page

    def _effects_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.shadow_slider = IntensitySlider(page)
        self.stroke_slider = IntensitySlider(page)
        self.glow_slider = IntensitySlider(page)
        self.gradient_slider = IntensitySlider(page)
        form.addRow('Drop shadow:', self.shadow_slider)
        form.addRow('Outline / stroke:', self.stroke_slider)
        form.addRow('Glow:', self.glow_slider)
        form.addRow('Background gradient:', self.gradient_slider)
        self.contrast_check = QCheckBox(
            'Automatic contrast: measure the artwork behind the text and '
            'reinforce shadow, outline and gradient only where needed', page)
        self.contrast_check.setToolTip(
            'Keeps light artwork readable without flattening the illustration.')
        form.addRow('', self.contrast_check)
        note = QLabel('100% = the intensity designed into the preset. '
                      '0% disables the effect entirely.', page)
        note.setWordWrap(True)
        form.addRow('', note)
        return page

    def _asian_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.asian_check = QCheckBox('Display Asian subtitle', page)
        form.addRow('', self.asian_check)
        self.asian_source = combo(page, [
            ('column', 'Read it from a calibre column'),
            ('manual', 'Use the fixed text below')])
        form.addRow('Source:', self.asian_source)
        self.asian_column = QLineEdit(page)
        self.asian_column.setPlaceholderText('#original_title')
        form.addRow('Custom column:', self.asian_column)
        self.asian_text = QLineEdit(page)
        form.addRow('Asian title:', self.asian_text)
        self.asian_mode = combo(page, [('auto', 'Preset default'),
                                       ('horizontal', 'Horizontal'),
                                       ('vertical', 'Vertical')])
        form.addRow('Mode:', self.asian_mode)
        self.asian_size = IntensitySlider(page, 40, 200)
        form.addRow('Size:', self.asian_size)
        note = QLabel(
            'No translation is ever invented. The chinese/korean/japanese text '
            'must come from a column you filled in (for example '
            '#original_title) or be typed by hand, in the settings or in the '
            'preview window.', page)
        note.setWordWrap(True)
        form.addRow('', note)
        return page

    def _metadata_tab(self):
        page = QWidget(self)
        form = form_layout(page)
        self.title_template = QLineEdit(page)
        self.title_template.setPlaceholderText('{title}')
        form.addRow('Title template:', self.title_template)
        self.author_template = QLineEdit(page)
        self.author_template.setPlaceholderText('{authors}')
        form.addRow('Author template:', self.author_template)
        self.swap_check = QCheckBox(
            'Swap author names stored as "Last, First"', page)
        form.addRow('', self.swap_check)
        self.library_picker = DirPicker(page, 'Choose your artwork folder',
                                        placeholder='Optional')
        form.addRow('Image library:', self.library_picker)
        self.mark_column = QLineEdit(page)
        self.mark_column.setPlaceholderText('#cover_style')
        form.addRow('Column to update:', self.mark_column)
        self.mark_value = QLineEdit(page)
        form.addRow('Value to write:', self.mark_value)
        note = QLabel(
            'Templates use the calibre template language, so {title}, '
            '{series}, {#original_title} and functions all work. Leave empty '
            'to use the plain metadata field. The column above, if set, is '
            'filled after a cover is generated so you can track your work.',
            page)
        note.setWordWrap(True)
        form.addRow('', note)
        return page

    @staticmethod
    def _wrap(layout):
        holder = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        holder.setLayout(layout)
        return holder

    # -- helpers -----------------------------------------------------------
    def _update_ratio(self):
        width = max(1, self.width_spin.value())
        self.ratio_label.setText('1 : %.3f  (2:3 = 1.500)'
                                 % (self.height_spin.value() / float(width)))

    def _update_preset_help(self):
        preset = presets_mod.get_preset(combo_value(self.preset_combo),
                                        self.settings.get('user_presets'))
        self.preset_help.setText(preset.get('description', ''))

    def _report_fonts(self):
        book = FontBook(self.font_title.value() or None,
                        self.font_author.value() or None,
                        self.font_cjk.value() or None)
        used = book.describe()
        chain = used.get('cjk_chain') or []
        self.font_report.setText(
            'Title: %s\nAuthor: %s\nCJK: %s\nCJK fallback chain: %s'
            % (used.get('title') or 'none found',
               used.get('author') or 'none found',
               used.get('cjk') or 'none found - install a CJK font to render '
                                  'chinese/korean text',
               ', '.join(chain[:6]) or 'empty'))

    def _refresh_styles(self):
        self.styles_combo.clear()
        for name in sorted(self.settings.get('saved_styles', {})):
            self.styles_combo.addItem(name)

    def _save_style(self):
        name, ok = QInputDialog.getText(self, 'Save style', 'Style name:')
        name = (name or '').strip()
        if not ok or not name:
            return
        current = self._collect()
        self.settings.setdefault('saved_styles', {})[name] = dict(
            (key, current[key]) for key in STYLE_KEYS if key in current)
        self._refresh_styles()
        index = self.styles_combo.findText(name)
        if index >= 0:
            self.styles_combo.setCurrentIndex(index)

    def _load_style(self):
        name = self.styles_combo.currentText()
        style = self.settings.get('saved_styles', {}).get(name)
        if not style:
            return
        self.settings.update(style)
        self._load()

    def _delete_style(self):
        name = self.styles_combo.currentText()
        if not name:
            return
        if QMessageBox.question(self, 'Delete style',
                                'Delete the style "%s"?' % name) != \
                QMessageBox.StandardButton.Yes:
            return
        self.settings.get('saved_styles', {}).pop(name, None)
        self._refresh_styles()

    # -- load / save -------------------------------------------------------
    def _set_combo(self, box, value):
        index = box.findData(value)
        box.setCurrentIndex(max(0, index))

    def _load(self):
        s = self.settings
        self.width_spin.setValue(int(s.get('width', 1600)))
        self.height_spin.setValue(int(s.get('height', 2400)))
        self.quality_spin.setValue(int(s.get('quality', 92)))
        self._set_combo(self.format_combo, s.get('output_format', 'JPEG'))
        self.backup_check.setChecked(bool(s.get('backup_covers', True)))
        self._update_ratio()

        self._set_combo(self.preset_combo, s.get('preset'))
        self._set_combo(self.title_pos_combo, s.get('title_position', 'auto'))
        self._set_combo(self.author_pos_combo, s.get('author_position', 'auto'))
        self.title_size.set_value(s.get('title_size_scale', 1.0))
        self.author_size.set_value(s.get('author_size_scale', 1.0))
        self.lines_spin.setValue(int(s.get('title_max_lines') or 0))
        self._set_combo(self.case_combo, s.get('title_case', 'auto'))
        self.series_check.setChecked(bool(s.get('show_series', True)))
        self.author_check.setChecked(bool(s.get('show_author', True)))
        self._refresh_styles()
        self._update_preset_help()

        self.font_title.set_value(s.get('font_title', ''))
        self.font_author.set_value(s.get('font_author', ''))
        self.font_cjk.set_value(s.get('font_cjk', ''))
        self._report_fonts()

        self.shadow_slider.set_value(s.get('shadow', 1.0))
        self.stroke_slider.set_value(s.get('stroke', 1.0))
        self.glow_slider.set_value(s.get('glow', 1.0))
        self.gradient_slider.set_value(s.get('gradient', 1.0))
        self.contrast_check.setChecked(bool(s.get('auto_contrast', True)))

        self.asian_check.setChecked(bool(s.get('asian_enabled')))
        self._set_combo(self.asian_source, s.get('asian_source', 'column'))
        self.asian_column.setText(s.get('asian_column', ''))
        self.asian_text.setText(s.get('asian_text', ''))
        self._set_combo(self.asian_mode, s.get('asian_mode', 'auto'))
        self.asian_size.set_value(s.get('asian_size_scale', 1.0))

        self.title_template.setText(s.get('title_template', ''))
        self.author_template.setText(s.get('author_template', ''))
        self.swap_check.setChecked(bool(s.get('author_swap')))
        self.library_picker.set_value(s.get('image_library', ''))
        self.mark_column.setText(s.get('mark_column', ''))
        self.mark_value.setText(s.get('mark_value', ''))

    def _collect(self):
        s = dict(self.settings)
        s.update({
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'quality': self.quality_spin.value(),
            'output_format': combo_value(self.format_combo, 'JPEG'),
            'backup_covers': self.backup_check.isChecked(),

            'preset': combo_value(self.preset_combo, presets_mod.DEFAULT_PRESET),
            'title_position': combo_value(self.title_pos_combo, 'auto'),
            'author_position': combo_value(self.author_pos_combo, 'auto'),
            'title_size_scale': self.title_size.value(),
            'author_size_scale': self.author_size.value(),
            'title_max_lines': self.lines_spin.value(),
            'title_case': combo_value(self.case_combo, 'auto'),
            'show_series': self.series_check.isChecked(),
            'show_author': self.author_check.isChecked(),

            'font_title': self.font_title.value(),
            'font_author': self.font_author.value(),
            'font_cjk': self.font_cjk.value(),

            'shadow': self.shadow_slider.value(),
            'stroke': self.stroke_slider.value(),
            'glow': self.glow_slider.value(),
            'gradient': self.gradient_slider.value(),
            'auto_contrast': self.contrast_check.isChecked(),

            'asian_enabled': self.asian_check.isChecked(),
            'asian_source': combo_value(self.asian_source, 'column'),
            'asian_column': self.asian_column.text().strip(),
            'asian_text': self.asian_text.text().strip(),
            'asian_mode': combo_value(self.asian_mode, 'auto'),
            'asian_size_scale': self.asian_size.value(),

            'title_template': self.title_template.text().strip(),
            'author_template': self.author_template.text().strip(),
            'author_swap': self.swap_check.isChecked(),
            'image_library': self.library_picker.value(),
            'mark_column': self.mark_column.text().strip(),
            'mark_value': self.mark_value.text().strip(),
        })
        return s

    def validate(self):
        if self.width_spin.value() < 400 or self.height_spin.value() < 600:
            QMessageBox.warning(self, 'Stylish Cover Generator',
                                'The output is very small; 1600x2400 is '
                                'recommended.')
        return True

    def save_settings(self):
        self.settings = self._collect()
        save_settings(self.settings)
