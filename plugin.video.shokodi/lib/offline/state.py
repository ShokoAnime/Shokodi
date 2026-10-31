# -*- coding: utf-8 -*-
"""
Offline state, shared between the plugin and script processes of a Kodi session.
It is only a hint: the plugin always tries the server first, and clears the flag on the first success.
"""
import os

import xbmcgui

from lib.utils.globalvars import plugin_addon, translatePath

_PROPERTY = 'shokodi.offline'


def is_offline():
    return xbmcgui.Window(10000).getProperty(_PROPERTY) == 'true'


def set_offline(offline):
    xbmcgui.Window(10000).setProperty(_PROPERTY, 'true' if offline else '')


def data_dir(*parts):
    """Gets (and creates) a folder in the addon's profile directory"""
    path = os.path.join(translatePath(plugin_addon.getAddonInfo('profile')), *parts)
    if not os.path.isdir(path):
        os.makedirs(path)
    return path
