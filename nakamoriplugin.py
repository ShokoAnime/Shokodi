import json
import sys

import debug
import error_handler
import nakamori_player
import routing
import xbmcplugin
from error_handler import try_function, show_messages, ErrorPriority
from kodi_models.kodi_models import DirectoryListing
from nakamori_utils import nakamoritools as nt
from nakamori_utils.globalvars import *

plugin_localize = plugin_addon.getLocalizedString
routing_plugin = routing.Plugin('plugin://plugin.video.nakamori')
url_for = routing_plugin.url_for


@routing_plugin.route('/')
def main():
    # start debugging, show main menu, first run wizard

    show_main_menu()


# Order matters on these. In this, it goes try -> route -> show_main_menu
# Python is retarded, as you'd expect the opposite
@routing_plugin.route('/menu/main')
@try_function(ErrorPriority.BLOCKING)
def show_main_menu():
    from shoko_models.v2 import Filter
    filter = Filter(0, build_full_object=True)
    dir = DirectoryListing('tvshows')
    items = []
    # this just throws an error. It's for testing and should be removed later.
    # filter = items[1]
    for item in filter:
        items.append(item)
    # apply settings for main menu
    items[:] = [x for x in items if not is_main_menu_item_enabled(x)]

    add_extra_main_menu_items(items)

    # sort the filters
    try:
        # if they are all zero, preserve server sorting
        if any(x.sort_index != 0 for x in items):
            items.sort(key=lambda a: (a.sort_index, a.name))
    except:
        error_handler.exception(ErrorPriority.HIGH)
    for item in items:
        dir.append(item.get_listitem())


def is_main_menu_item_enabled(item):
    """

    :param item:
    :type item: Filter
    :return:
    """
    # This only has one at the moment, but we may add the ability for more later
    if item.name == 'Unsorted Files' and not plugin_addon.getSetting('show_unsort') == 'true':
        return False


def add_extra_main_menu_items(items):
    """
    Add items like search, calendar, etc
    :param items:
    :return:
    """
    from shoko_models.v2 import CustomItem
    # { 'Airing Today': 0, 'Calendar': 1, 'Seasons': 2, 'Years': 3, 'Tags': 4, 'Unsort': 5, 'Settings': 7,
    # 'Shoko Menu': 8, 'Search': 9 }
    if plugin_addon.getSetting('show_airing_today') == 'true':
        items.append(CustomItem(plugin_localize(30223), 'airing.png', url_for(show_airing_today_menu), 1))

    # if plugin_addon.getSetting('show_calendar') == 'true':
    #    items.append(CustomItem(plugin_localize(30222), 'calendar.png', script47replace(nakamoriscript.calendar), 2))

    # if plugin_addon.getSetting('show_settings') == 'true':
    #    items.append(CustomItem(plugin_localize(30107), 'settings.png', script47replace(nakamoriscript.show_settings_dialog), 7))

    if plugin_addon.getSetting('show_shoko') == 'true':
        items.append(CustomItem(plugin_localize(30115), 'settings.png', url_for(show_shoko_menu), 8))

    if plugin_addon.getSetting('show_search') == 'true':
        items.append(CustomItem(plugin_localize(30221), 'search.png', url_for(show_search_menu), 9))


@routing_plugin.route('/menu/filter/byid/<filter_id>')
@try_function(ErrorPriority.BLOCKING)
def show_filter_menu(filter_id):
    from shoko_models.v2 import Filter
    f = Filter(filter_id, build_full_object=True, get_children=True)
    d = DirectoryListing('tvshows')
    for item in f:
        d.append(item.get_listitem())


# do not make urls like /menu/filter/<filter_id> and /menu/filter/unsorted, as they will conflict randomly
@routing_plugin.route('/menu/filter/unsorted')
@try_function(ErrorPriority.BLOCKING)
def show_unsorted_menu():
    # this is really bad practice, but the unsorted files list is too special
    from shoko_models.v2 import File
    url = server + '/api/file/unsort'
    json_body = nt.get_json(url, True)
    json_node = json.loads(json_body)

    dir = DirectoryListing('episodes')
    for item in json_node:
        f = File(item)
        dir.append(f.get_listitem(), False)


@routing_plugin.route('/menu/group/<group_id>/filterby/<filter_id>')
@try_function(ErrorPriority.BLOCKING)
def show_group_menu(group_id, filter_id):
    from shoko_models.v2 import Group
    group = Group(group_id, build_full_object=True, get_children=True, filter_id=filter_id)
    dir = DirectoryListing('tvshows')
    for item in group:
        dir.append(item.get_listitem())


@routing_plugin.route('/menu/series/<series_id>')
@try_function(ErrorPriority.BLOCKING)
def show_series_menu(series_id):
    from shoko_models.v2 import Series
    series = Series(series_id, build_full_object=True, get_children=True)

    if len(series.episode_types) > 1:
        dir = DirectoryListing('seasons')
        # type listing
        for item in series.episode_types:
            dir.append(item.get_listitem())
    else:
        dir = DirectoryListing('episodes')
        for item in series:
            int_add_episode(item, dir)


@routing_plugin.route('/menu/series/<series_id>/type/<episode_type>')
def show_series_episode_types_menu(series_id, episode_type):
    from shoko_models.v2 import SeriesTypeList
    types = SeriesTypeList(series_id, episode_type)
    dir = DirectoryListing('episodes')
    for item in types:
        int_add_episode(item, dir)


@try_function(ErrorPriority.HIGHEST, 'Failed to Add an Episode')
def int_add_episode(item, dir):
    if item.get_file() is None:
        return
    dir.append(item.get_listitem(), False)


@routing_plugin.route('/menu/airing_today')
@try_function(ErrorPriority.BLOCKING)
def show_airing_today_menu():
    pass


@routing_plugin.route('/menu/calendar_old')
@try_function(ErrorPriority.BLOCKING)
def show_calendar_menu():
    pass


@routing_plugin.route('/menu/search')
@try_function(ErrorPriority.BLOCKING)
def show_search_menu():
    pass


@routing_plugin.route('/menu/shoko')
@try_function(ErrorPriority.BLOCKING)
def show_shoko_menu():
    pass


def play_video_internal(ep_id, file_id, mark_as_watched=True, resume=False):
    # this prevents the spinning wheel
    xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False, updateListing=False, cacheToDisc=False)
    # all of real work is done here
    nakamori_player.play_video(file_id, ep_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play')
@try_function(ErrorPriority.BLOCKING)
def play_video(ep_id, file_id):
    play_video_internal(ep_id, file_id)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play_without_marking')
def play_video_without_marking(ep_id, file_id):
    play_video_internal(ep_id, file_id, mark_as_watched=False)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/resume')
def resume_video(ep_id, file_id):
    # if we are resuming, then we'll assume that scrobbling and marking are True
    play_video_internal(ep_id, file_id, mark_as_watched=True, resume=True)


@try_function(ErrorPriority.BLOCKING)
def _main():
    debug.debug_init()
    auth, apikey = try_function(ErrorPriority.BLOCKING)(nt.valid_user)()
    if not auth:
        raise RuntimeError('Wrong Username or Password, or unable to connect to the server.')
    try_function(ErrorPriority.BLOCKING)(routing_plugin.run)()
    show_messages()


if __name__ == '__main__':
    _main()
