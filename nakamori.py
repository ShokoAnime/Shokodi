# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import lib.guibuilder as gb
from nakamori_utils import kodi_utils, shoko_utils
from nakamori_utils.globalvars import *
import search

import xbmcgui
import xbmc

import sys
from proxy.python_version_proxy import python_proxy as pyproxy

if sys.version_info[0] < 3:
    # noinspection PyCompatibility
    from urllib2 import HTTPError
else:
    # For Python 3.0 and later
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.error import HTTPError


if plugin_addon.getSetting('wizard') != '0' and shoko_utils.get_server_status():
    try:
        parameters = pyproxy.parse_parameters('')
        mode = None
        if parameters:
            if 'mode' in parameters and parameters['mode'] is not None:
                mode = int(parameters['mode'])

        try:
            if 'cmd' in parameters:
                cmd = parameters['cmd']
            else:
                cmd = None
        except Exception as exp:
            cmd = None

        if cmd is not None:
            if cmd == 'viewCast':
                gb.build_cast_menu(parameters)
            elif cmd == 'searchCast':
                gb.search_for(parameters.get('url', ''))
            elif cmd == 'playlist':
                # kodi_utils.play_continue_item()
                pass
            elif cmd == 'mediainfo':
                shoko_utils.mediainfo_update()
            elif cmd == 'statsupdate':
                shoko_utils.stats_update()
            elif cmd == 'folderlist':
                shoko_utils.folder_list()
            elif cmd == 'createPlaylist':
                gb.create_playlist(parameters['serie_id'])
        else:
            if mode == 7:  # Playlist -continue-
                # kodi_utils.play_continue_item()
                pass
            elif mode == 9:  # Calendar
                if plugin_addon.getSetting('calendar_basic') == 'true':
                    gb.build_serie_soon(parameters)
                # else:
                    # nt.calendar()
            elif mode == 31:  # Clear Search History
                search.clear_search_history(parameters)
            elif mode == 32:  # remove watch marks from kodi db
                kodi_utils.fix_mark_watch_in_kodi_db()
            elif mode == 33:  # clear image cache from kodi db
                kodi_utils.clear_image_cache_in_kodi_db()
    except HTTPError as err:
        if err.code == 401:
            xbmc.log('--- (httperror = 401: wizard) ---', xbmc.LOGWARNING)
            # gb.build_network_menu()
else:
    # gb.build_network_menu()
    if xbmcgui.Dialog().yesno('Error Connecting', 'Would you like to open the setup wizard'):
        xbmc.log('--- (get_server_status: wizard) ---', xbmc.LOGWARNING)
        plugin_addon.setSetting(id='wizard', value='0')
        # nt.wizard()
