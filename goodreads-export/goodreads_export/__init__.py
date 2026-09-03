#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goodreads Export - a calibre interface plugin.

Writes a CSV that Goodreads' "Import books" page accepts, with the exact
column names it expects, and the conversions it needs: ratings halved from
calibre's 0..10 scale, tags turned into shelves, dates cleaned up.

Only this file is loaded when calibre scans the plugins, so it stays free of
Qt imports; the real work is loaded lazily from action.py.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from calibre.customize import InterfaceActionBase


class GoodreadsExport(InterfaceActionBase):

    name = 'Goodreads Export'
    description = ('Export your books to a CSV that Goodreads can import: '
                   'exact column names, ratings converted to whole stars, '
                   'tags turned into shelves.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'huosh1'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.goodreads_export.action:GoodreadsExportAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.goodreads_export.config import ConfigWidget
            return ConfigWidget()
        return None

    def save_settings(self, config_widget):
        config_widget.save_settings()
