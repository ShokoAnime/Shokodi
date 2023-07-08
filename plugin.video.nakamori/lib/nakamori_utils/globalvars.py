#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import xbmcaddon

try:
    import xbmcvfs
    translatePath = xbmcvfs.translatePath
except (ImportError, NameError, AttributeError):
    import xbmc
    translatePath = xbmc.translatePath

# in kodi 18, this will just work, but in kodi <18, these are regenerated each time this is called.
# We can make this an object belonging to nakamori.service, but we may need to make script and plugin
# dependent on service if that is the case

# The plugin object for nakamori.plugin
plugin_addon = xbmcaddon.Addon('plugin.video.nakamori')
plugin_version = plugin_addon.getAddonInfo('version')
plugin_home = translatePath(plugin_addon.getAddonInfo('path'))
plugin_img_path = os.path.join(plugin_addon.getAddonInfo('path'), 'resources', 'media')

server = 'http://' + plugin_addon.getSetting('ipaddress') + ':' + plugin_addon.getSetting('port')

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
