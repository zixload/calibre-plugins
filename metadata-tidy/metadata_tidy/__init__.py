#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Metadata Tidy - a calibre interface plugin.

Pulls the series name and the volume number out of titles that carry them
("La guerre du pavot T1", "Vagabond part 02", "Vol. 1: Subtitle") and fills
the Series and Series index fields, so covers, sorting and grouping finally
work.

Only this file is loaded when calibre scans the plugins, so it stays free of
Qt imports; the real work is loaded lazily from action.py.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from calibre.customize import InterfaceActionBase


class MetadataTidy(InterfaceActionBase):

    name = 'Metadata Tidy'
    description = ('Extract the series and the volume number from book '
                   'titles, clean up titles and author names, with a preview '
                   'of every change and a one click undo.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'huosh1'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.metadata_tidy.action:MetadataTidyAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.metadata_tidy.config import ConfigWidget
            return ConfigWidget()
        return None

    def save_settings(self, config_widget):
        config_widget.save_settings()
