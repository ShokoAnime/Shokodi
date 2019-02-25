# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json

import lib.debug as dbg
import lib.guibuilder as gb
from nakamori_utils import nakamoritools as nt
from nakamori_utils.globalvars import *
from lib import kodi_utils, shoko_utils, search

import xbmcplugin
import xbmcaddon
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

dbg.debug_init()

nt.wizard()


def play_video(video_parameters):
    """
    play function
    :param video_parameters: dictionary with parameters to ask shoko for url
    :return:
    """
    global win, ctl, ui_index, exp
    try:
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        ctl = win.getControl(win.getFocusId())
        if kodi_utils.play_video(video_parameters['ep_id'],
                                 video_parameters['raw_id'] if 'raw_id' in video_parameters else "0",
                                 video_parameters['movie'] if 'movie' in video_parameters else 0) > 0:
            # noinspection PyTypeChecker
            ui_index = video_parameters.get('ui_index', '')
            if ui_index != '':
                nt.move_position_on_list(ctl, int(ui_index) + 1)
            video_parameters['watched'] = True
            nt.mark_watch_status(video_parameters)
    except Exception as exp:
        xbmc.log('---> play_video ' + str(exp), xbmc.LOGWARNING)
        pass


if plugin_addon.getSetting('wizard') != '0' and nt.get_server_status():
    try:
        auth, apikey = nt.valid_user()
        if auth:
            try:
                parameters = pyproxy.parse_parameters(sys.argv[2])
            except Exception as exp:
                nt.error('valid_userid_1 parse_parameters() util.error', str(exp))
                parameters = {'mode': 2}

            mode = None
            if parameters:
                try:
                    if 'mode' in parameters and parameters['mode'] is not None:
                        mode = int(parameters['mode'])
                except Exception as exp:
                    nt.error('valid_userid set \'mode\' util.error', str(exp) + " parameters: " + str(parameters))

            try:
                if 'cmd' in parameters:
                    cmd = parameters['cmd']
                else:
                    cmd = None
            except Exception as exp:
                nt.error('valid_userid_2 parse_parameters() util.error', str(exp))
                cmd = None

            if cmd is not None:
                if cmd == "voteSer":
                    nt.vote_series(parameters['serie_id'])
                elif cmd == "voteEp":
                    nt.vote_episode(parameters['ep_id'])
                elif cmd == "viewCast":
                    gb.build_cast_menu(parameters)
                elif cmd == "searchCast":
                    gb.search_for(parameters.get('url', ''))
                elif cmd == "watched":
                    if nt.get_kodi_setting_int('videolibrary.tvshowsselectfirstunwatcheditem') == 0 or \
                            plugin_addon.getSetting("select_unwatched") == "true":
                        try:
                            win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                            ctl = win.getControl(win.getFocusId())
                            # noinspection PyTypeChecker
                            ui_index = parameters.get('ui_index', '')
                            if ui_index != '':
                                nt.move_position_on_list(ctl, int(ui_index) + 1)
                        except Exception as exp:
                            xbmc.log(str(exp), xbmc.LOGWARNING)
                            pass
                    parameters['watched'] = True
                    nt.mark_watch_status(parameters)
                    if plugin_addon.getSetting("vote_always") == "true":
                        if parameters.get('userrate', 0) == 0:
                            nt.vote_episode(parameters['ep_id'])
                elif cmd == "unwatched":
                    parameters['watched'] = False
                    nt.mark_watch_status(parameters)
                elif cmd == "playlist":
                    kodi_utils.play_continue_item()
                elif cmd == "no_mark":
                    plugin_addon.setSetting('no_mark', '1')
                    # noinspection PyTypeChecker
                    play_video(parameters)
                elif cmd == "pickFile":
                    if str(parameters['ep_id']) != "0":
                        ep_url = server + "/api/ep?id=" + str(parameters['ep_id']) + "&level=2"
                        kodi_utils.file_list_gui(json.loads(nt.get_json(ep_url)))
                elif cmd == 'rescan':
                    shoko_utils.rescan_file(parameters.get('vl', ''))
                elif cmd == 'rehash':
                    shoko_utils.rehash_file(parameters.get('vl', ''))
                elif cmd == 'missing':
                    shoko_utils.remove_missing_files()
                elif cmd == 'mediainfo':
                    shoko_utils.mediainfo_update()
                elif cmd == 'statsupdate':
                    shoko_utils.stats_update()
                elif cmd == 'folderlist':
                    shoko_utils.folder_list()
                elif cmd == 'createPlaylist':
                    gb.create_playlist(parameters['serie_id'])
                elif cmd == 'refresh':
                    nt.refresh()
                elif cmd == 'resume':
                    plugin_addon.setSetting('resume', '1')
                    # noinspection PyTypeChecker
                    play_video(parameters)
                elif cmd == 'resumeno_mark':
                    plugin_addon.setSetting('no_mark', '1')
                    plugin_addon.setSetting('resume', '1')
                    # noinspection PyTypeChecker
                    play_video(parameters)
                elif cmd == 'wizard':
                    xbmc.log('--- (cmd: wizard) --- ', xbmc.LOGWARNING)
                    plugin_addon.setSetting('wizard', '0')
                    nt.wizard()
            else:
                if mode == 0:  # string label
                    pass
                elif mode == 1:  # play_file
                    play_video(parameters)
                elif mode == 2:  # DIRECTORY
                    xbmcgui.Dialog().ok('MODE=2', 'MODE')
                elif mode == 3:  # Search
                    try:
                        if 'extras' in parameters:
                            if parameters['extras'] == "force-search" and 'query' in parameters:
                                url = server + '/api/search'
                                url = pyproxy.set_parameter(url, 'query', parameters['query'])
                                gb.search_for(url)
                            else:
                                xbmcplugin.setContent(int(gb.handle), 'movies')
                                gb.execute_search_and_add_query()
                        else:
                            gb.build_search_directory()
                    except Exception as search_ex:
                        xbmc.log('---> search, mode=3:' + str(search_ex), xbmc.LOGERROR)
                        gb.build_search_directory()
                elif mode == 4:  # Group/Serie
                    try:
                        if dbg.has_line_profiler:
                            # noinspection PyUnresolvedReferences
                            profiler = dbg.line_profiler.LineProfiler()
                            profiler.add_function(gb.build_groups_menu)
                            profiler.enable_by_count()
                        gb.build_groups_menu(parameters)
                    finally:
                        if dbg.has_line_profiler:
                            # noinspection PyUnboundLocalVariable
                            profiler.print_stats(open('stats.txt', 'w'))
                elif mode == 5:  # Serie EpisodeTypes (episodes/ovs/credits)
                    gb.build_serie_episodes_types(parameters)
                elif mode == 6:  # Serie Episodes (list of episodes)
                    gb.build_serie_episodes(parameters)
                elif mode == 7:  # Playlist -continue-
                    kodi_utils.play_continue_item()
                elif mode == 8:  # File List
                    gb.build_raw_list(parameters)
                elif mode == 9:  # Calendar
                    if plugin_addon.getSetting('calendar_basic') == 'true':
                        gb.build_serie_soon(parameters)
                    else:
                        nt.calendar()
                elif mode == 10:  # newCalendar
                    nt.calendar()
                    # gb.build_serie_soon_new(parameters)
                elif mode == 11:  # Settings
                    # noinspection PyTypeChecker
                    xbmcaddon.Addon(id='plugin.video.nakamori').openSettings()
                elif mode == 12:  # Shoko
                    gb.build_shoko_menu()
                elif mode == 13:  # Experiment
                    nt.calendar()
                elif mode == 31:  # Clear Search History
                    search.clear_search_history(parameters)
                elif mode == 32:  # remove watch marks from kodi db
                    kodi_utils.fix_mark_watch_in_kodi_db()
                elif mode == 33:  # clear image cache from kodi db
                    kodi_utils.clear_image_cache_in_kodi_db()
                else:
                    # starting point
                    gb.build_filters_menu()
        else:
            xbmc.log('--- (auth = False: wizard) ---', xbmc.LOGWARNING)
            nt.error(plugin_addon.getLocalizedString(30194), plugin_addon.getLocalizedString(30195))
            plugin_addon.setSetting(id='wizard', value='0')
    except HTTPError as err:
        if err.code == 401:
            xbmc.log('--- (httperror = 401: wizard) ---', xbmc.LOGWARNING)
            gb.build_network_menu()
else:
    gb.build_network_menu()
    if xbmcgui.Dialog().yesno("Error Connecting", "Would you like to open the setup wizard"):
        xbmc.log('--- (get_server_status: wizard) ---', xbmc.LOGWARNING)
        plugin_addon.setSetting(id='wizard', value='0')
        nt.wizard()
