#!/usr/bin/env python
# -*- coding: utf-8 -*-
import nakamoriplayer
from lib import debug
from lib import search
import xbmcgui

import routing
from lib.error_handler import spam, ErrorPriority, try_function, show_messages
from lib.nakamori_utils import kodi_utils, shoko_utils
from lib.proxy.python_version_proxy import python_proxy as pyproxy

from lib.nakamori_utils.globalvars import *

script = routing.Script(base_url=os.path.split(__file__)[-1], convert_args=True)


@script.route('/')
def root():
    items = [
        (plugin_addon.getLocalizedString(30025), (wizard_connection, [])),
        (plugin_addon.getLocalizedString(30043), (wizard_login, [])),
    ]

    options = []
    for item in items:
        options.append(item[0])

    result = xbmcgui.Dialog().contextmenu(options)
    if result >= 0:
        action, args = items[result][1]
        action(*args)


@script.route('/seriesinfo/aid/<aid>/')
def series_info(aid=0):
    from lib.windows import series_info as info
    info.open_seriesinfo(aid=aid)


@script.route('/seriesinfo/<aid>/')
def series_info(id=0):
    from lib.windows import series_info as info
    info.open_seriesinfo(id=id)


@script.route('/arbiter/<wait>/<path:arg>')
@try_function(ErrorPriority.BLOCKING)
def arbiter(wait, arg):
    spam('arbiting', 'wait:', wait, 'arg:', arg)
    if wait is None or arg is None:
        raise RuntimeError('Arbiter received no parameters')
    xbmc.sleep(wait)
    xbmc.executebuiltin(arg)


@script.route('/dialog/wizard/connection')
def wizard_connection():
    from lib.windows import wizard
    wizard.open_connection_wizard()


@script.route('/dialog/wizard/login')
def wizard_login():
    from lib.windows import wizard
    wizard.open_login_wizard()


@script.route('/dialog/shoko')
@try_function(ErrorPriority.BLOCKING)
def shoko_menu():
    # TODO add things
    # Remove Missing
    # Import Folders?
    # various other actions
    items = [
        (plugin_addon.getLocalizedString(30049), (shoko_utils.run_import, [])),
        (plugin_addon.getLocalizedString(30042), (shoko_utils.remove_missing_files, []))
    ]

    options = []
    for item in items:
        options.append(item[0])

    result = xbmcgui.Dialog().contextmenu(options)
    if result >= 0:
        action, args = items[result][1]
        action(*args)


@script.route('/search/remove/<path:query>')
def remove_search_term(query):
    search.remove_search_history(query)
    refresh()


@script.route('/search/clear')
def clear_search():
    search.remove_search_history()
    refresh()


@script.route('/kodi/clear_image_cache')
def clear_image_cache():
    kodi_utils.clear_image_cache()


@script.route('/kodi/clear_listitem_cache')
def clear_listitem_cache():
    kodi_utils.clear_listitem_cache()


@script.route('/refresh')
def refresh():
    kodi_utils.refresh()


@script.route('/dialog/vote_series/<series_id>/')
@try_function(ErrorPriority.BLOCKING)
def show_series_vote_dialog(series_id):
    # TODO something ?
    pass


@script.route('/dialog/vote_episode/<ep_id>/')
@try_function(ErrorPriority.BLOCKING)
def show_episode_vote_dialog(ep_id):
    # TODO something ?
    pass


@script.route('/series/<series_id>/vote')
@try_function(ErrorPriority.BLOCKING)
def vote_for_series(series_id):
    from lib.shoko_models.v2 import Series
    series = Series(series_id)
    suggest_rating = ''
    if plugin_addon.getSetting('suggest_series_vote') == 'true':
        if plugin_addon.getSetting('suggest_series_vote_all_eps') == 'true':
            if not series.did_you_rate_every_episode:
                xbmcgui.Dialog().ok(plugin_addon.getLocalizedString(30353))
                return
        suggest_rating = ' [ %s ]' % series.suggest_rating_based_on_episode_rating

    vote_list = ['Don\'t Vote' + suggest_rating, '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
    my_vote = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30023), vote_list)
    if my_vote < 1:
        return
    my_vote = pyproxy.safe_int(vote_list[my_vote])
    if my_vote < 1:
        return
    series.vote(my_vote)


@script.route('/episode/<ep_id>/vote')
@try_function(ErrorPriority.BLOCKING)
def vote_for_episode(ep_id):
    from lib.shoko_models.v2 import Episode
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
    my_vote = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30023), vote_list)
    if my_vote < 1:
        return
    my_vote = pyproxy.safe_int(vote_list[my_vote])
    if my_vote < 1:
        return
    ep = Episode(ep_id)
    ep.vote(my_vote)


@script.route('/tvshows/<vote_type>/vote')
@try_function(ErrorPriority.BLOCKING)
def vote_for_tvshows(vote_type):
    from lib.kodi_models import VideoLibraryItem
    vl_item = VideoLibraryItem()
    vl_item.vote(vote_type)


@script.route('/ep/<ep_id>/file_list')
@try_function(ErrorPriority.BLOCKING)
def file_list(ep_id):
    from lib.shoko_models.v2 import Episode
    ep = Episode(ep_id, build_full_object=True)
    items = [(x.name, x.id) for x in ep]
    selected_id = kodi_utils.show_file_list(items)
    nakamoriplayer.play_video(file_id=selected_id, ep_id=ep_id)


@script.route('/file/<file_id>/rescan')
@try_function(ErrorPriority.BLOCKING)
def rescan_file(file_id):
    from lib.shoko_models.v2 import File
    f = File(file_id)
    f.rescan()


@script.route('/file/<file_id>/rehash')
@try_function(ErrorPriority.BLOCKING)
def rehash_file(file_id):
    from lib.shoko_models.v2 import File
    f = File(file_id)
    f.rehash()


@script.route('/file/<file_id>/probe')
@try_function(ErrorPriority.BLOCKING)
def probe_file(file_id):
    from lib.shoko_models.v2 import File
    f = File(file_id, build_full_object=True)
    file_url = f.url_for_player
    content = '"file":"' + file_url + '"'
    schema = 'https' if plugin_addon.getSetting('use_https') == 'true' else 'http'
    url = schema + '://%s:%s/api/probe/%s' % (plugin_addon.getSetting('ipEigakan'), plugin_addon.getSetting('portEigakan'), file_id)
    busy = xbmcgui.DialogProgress()
    # TODO lang fix
    busy.create('Please wait', 'Probing')
    data = pyproxy.post_json(url, content)
    busy.close()
    xbmcgui.Dialog().ok('probe results', '%s' % data)


@script.route('/episode/<ep_id>/set_watched/<watched>')
@try_function(ErrorPriority.HIGH, 'Error Setting Watched Status')
def set_episode_watched_status(ep_id, watched):
    from lib.shoko_models.v2 import Episode
    ep = Episode(ep_id)
    ep.set_watched_status(watched)
    if plugin_addon.getSetting('sync_to_library') == 'true':
        playcount = '1' if watched else '0'
        # lastplayed = 'string'
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"playcount": ' + playcount + ' , "episodeid": ' + ep_id + '}, "id": 1 }')
    kodi_utils.refresh()


@script.route('/series/<series_id>/set_watched/<watched>')
@try_function(ErrorPriority.HIGH, 'Error Setting Watched Status')
def set_series_watched_status(series_id, watched):
    from lib.shoko_models.v2 import Series
    series = Series(series_id)
    series.set_watched_status(watched)
    kodi_utils.refresh()


@script.route('/group/<group_id>/set_watched/<watched>')
def set_group_watched_status(group_id, watched):
    from lib.shoko_models.v2 import Group
    group = Group(group_id)
    group.set_watched_status(watched)
    kodi_utils.refresh()


@script.route('/menu/episode/move_to_item/<index>/')
def move_to_index(index):
    kodi_utils.move_to_index(index)


if __name__ == '__main__':
    debug.debug_init()
    try_function(ErrorPriority.BLOCKING)(script.run)()
    show_messages()
