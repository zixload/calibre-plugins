#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build the dialog and exercise the no-device paths, without a Kobo attached.

    calibre-debug tools/gui_smoke.py
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import calibre.customize.ui  # noqa: F401  installs the plugin import hook
from calibre.gui2 import Application

from calibre_plugins.kobo_cover_pusher import pusher
from calibre_plugins.kobo_cover_pusher.config import ConfigWidget, get_settings


class FakeGui(object):
    device_manager = None


def main():
    app = Application([])  # noqa: F841 needed to build widgets

    settings = get_settings()
    print('settings: %d keys' % len(settings))

    widget = ConfigWidget()
    missing = [k for k in settings if k not in widget._collect()]
    print('ConfigWidget OK, unmapped keys: %s' % (missing or 'none'))
    widget.use_driver.setChecked(False)
    print('override box enabled when driver settings are off: %s'
          % widget.box.isEnabled())

    try:
        pusher.connected_kobo(FakeGui())
        print('FAIL: no device should have raised')
        return 1
    except pusher.DeviceError as err:
        print('no device -> %s' % str(err).split('.')[0])

    class NotAKobo(object):
        pass

    class Manager(object):
        connected_device = NotAKobo()

    class Gui(object):
        device_manager = Manager()

    try:
        pusher.connected_kobo(Gui())
        print('FAIL: a non Kobo device should have raised')
        return 1
    except pusher.DeviceError as err:
        print('wrong device -> %s' % str(err).split('(')[0].strip())

    fake = dict(use_driver_settings=False, keep_aspect=True, png=True)
    options = pusher.driver_options(object(), fake)
    print('override options: keep_cover_aspect=%s png_covers=%s'
          % (options['keep_cover_aspect'], options['png_covers']))
    widget.grab().save('docs/settings.png')
    print('screenshot saved')
    return 0


if __name__ == '__main__':
    sys.exit(main())
