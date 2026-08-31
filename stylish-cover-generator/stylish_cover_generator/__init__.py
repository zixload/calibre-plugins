#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stylish Cover Generator - a calibre interface plugin.

Turns the artwork a book already has into a real webnovel / dark fantasy cover
by compositing typography over it, then saves the result as the book cover.

Only this file is loaded when calibre scans the plugins, so it stays free of
Qt and Pillow imports; the real work is loaded lazily from action.py.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from calibre.customize import InterfaceActionBase


class StylishCoverGenerator(InterfaceActionBase):

    name = 'Stylish Cover Generator'
    description = ('Generate stylish book covers from the existing cover art '
                   'and the metadata: dark fantasy, webnovel, wuxia or minimal '
                   'presets, with automatic contrast and CJK support.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'huosh1'
    version = (1, 0, 1)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.stylish_cover_generator.action:StylishCoverAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.stylish_cover_generator.config import ConfigWidget
            return ConfigWidget()
        return None

    def save_settings(self, config_widget):
        config_widget.save_settings()
        if self.actual_plugin_:
            self.actual_plugin_.apply_settings()
