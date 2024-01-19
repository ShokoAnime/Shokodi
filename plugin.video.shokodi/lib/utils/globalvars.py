#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from lib import routing

try:
    import xbmcvfs
    translatePath = xbmcvfs.translatePath
except (ImportError, NameError, AttributeError):
    import xbmc
    # noinspection PyUnresolvedReferences
    translatePath = xbmc.translatePath


# The plugin object for nakamori.plugin
import xbmcaddon
plugin_addon = xbmcaddon.Addon()
plugin_version = plugin_addon.getAddonInfo('version')
plugin_home = translatePath(plugin_addon.getAddonInfo('path'))
plugin_img_path = os.path.join(plugin_addon.getAddonInfo('path'), 'resources', 'media')

schema = 'https' if plugin_addon.getSetting('use_https') == 'true' else 'http'
server = schema + '://' + plugin_addon.getSetting('ipaddress') + ':' + plugin_addon.getSetting('port')

tag_setting_flags = 0
tag_setting_flags |= 1 << 0 if plugin_addon.getSetting('MiscTags') == 'true' else 0
tag_setting_flags |= 1 << 1 if plugin_addon.getSetting('ArtTags') == 'true' else 0
tag_setting_flags |= 1 << 2 if plugin_addon.getSetting('SourceTags') == 'true' else 0
tag_setting_flags |= 1 << 3 if plugin_addon.getSetting('UsefulMiscTags') == 'true' else 0
tag_setting_flags |= 1 << 4 if plugin_addon.getSetting('SpoilerTags') == 'true' else 0
tag_setting_flags |= 1 << 5 if plugin_addon.getSetting('SettingTags') == 'true' else 0
tag_setting_flags |= 1 << 6 if plugin_addon.getSetting('ProgrammingTags') == 'true' else 0
tag_setting_flags |= 1 << 7 if plugin_addon.getSetting('GenreTags') == 'true' else 0
tag_setting_flags |= 1 << 31 if plugin_addon.getSetting('InvertTags') == 'Show' else 0

plugin_router = routing.Plugin('plugin.video.shokodi', convert_args=True)
script_router = routing.Script('plugin.video.shokodi', convert_args=True)
