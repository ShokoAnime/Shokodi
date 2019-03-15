import json

import debug
import error_handler
import nakamori_player
import routing
from error_handler import try_function, show_messages, ErrorPriority
from kodi_models import DirectoryListing
from nakamori_utils import kodi_utils, shoko_utils, script_utils
from proxy.python_version_proxy import python_proxy as pyproxy
from nakamori_utils.globalvars import *

plugin_localize = plugin_addon.getLocalizedString
routing_plugin = routing.Plugin('plugin://plugin.video.nakamori')
url_for = routing_plugin.url_for

# I had to read up on this. Functions have read access to this if they don't declare a plugin_dir
# if you want to do something like del plugin_dir, then you need to do this:
# def play():
#     global plugin_dir
#     del plugin_dir
plugin_dir = DirectoryListing()


def fail_menu():
    plugin_dir.success = False


# Order matters on these. In this, it goes try -> route -> show_main_menu
# Python is retarded, as you'd expect the opposite
@routing_plugin.route('/')
@try_function(ErrorPriority.BLOCKING)
def show_main_menu():
    from shoko_models.v2 import Filter
    f = Filter(0, build_full_object=True)
    plugin_dir.set_content('tvshows')
    items = []

    for item in f:
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
        plugin_dir.append(item.get_listitem())


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

    if plugin_addon.getSetting('show_calendar') == 'true':
        items.append(CustomItem(plugin_localize(30222), 'calendar.png', script(script_utils.url_calendar()), 2))

    if plugin_addon.getSetting('show_settings') == 'true':
        items.append(CustomItem(plugin_localize(30107), 'settings.png', script(script_utils.url_settings()), 7))

    if plugin_addon.getSetting('show_shoko') == 'true':
        items.append(CustomItem(plugin_localize(30115), 'settings.png', script(script_utils.url_shoko_menu()), 8))

    if plugin_addon.getSetting('show_search') == 'true':
        items.append(CustomItem(plugin_localize(30221), 'search.png', url_for(show_search_menu), 9))


@routing_plugin.route('/menu/filter/<filter_id>')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_filter_menu(filter_id):
    from shoko_models.v2 import Filter
    f = Filter(filter_id, build_full_object=True, get_children=True)
    plugin_dir.set_content('tvshows')
    plugin_dir.set_cached()
    f.apply_sorting(routing_plugin.handle)
    for item in f:
        plugin_dir.append(item.get_listitem())


@routing_plugin.route('/menu/filter/unsorted')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_unsorted_menu():
    # this is really bad practice, but the unsorted files list is too special
    from shoko_models.v2 import File
    url = server + '/api/file/unsort'
    json_body = pyproxy.get_json(url, True)
    json_node = json.loads(json_body)

    plugin_dir.set_content('episodes')
    for item in json_node:
        f = File(item)
        plugin_dir.append(f.get_listitem(), False)


@routing_plugin.route('/menu/group/<group_id>/filterby/<filter_id>')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_group_menu(group_id, filter_id):
    from shoko_models.v2 import Group
    group = Group(group_id, build_full_object=True, get_children=True, filter_id=filter_id)
    plugin_dir.set_content('tvshows')
    group.apply_sorting(routing_plugin.handle)
    for item in group:
        plugin_dir.append(item.get_listitem())


@routing_plugin.route('/menu/series/<series_id>')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_series_menu(series_id):
    from shoko_models.v2 import Series
    series = Series(series_id, build_full_object=True, get_children=True)

    if len(series.episode_types) > 1:
        plugin_dir.set_content('seasons')
        # type listing
        for item in series.episode_types:
            plugin_dir.append(item.get_listitem())
    else:
        plugin_dir.set_content('episodes')
        series.apply_sorting(routing_plugin.handle)
        for item in series:
            int_add_episode(item, plugin_dir)


@routing_plugin.route('/menu/series/<series_id>/type/<episode_type>')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_series_episode_types_menu(series_id, episode_type):
    from shoko_models.v2 import SeriesTypeList
    types = SeriesTypeList(series_id, episode_type)
    plugin_dir.set_content('episodes')
    types.apply_sorting(routing_plugin.handle)
    for item in types:
        int_add_episode(item, plugin_dir)


@try_function(ErrorPriority.HIGHEST, 'Failed to Add an Episode')
def int_add_episode(item, d):
    if item.get_file() is None:
        return
    d.append(item.get_listitem(), False)


@routing_plugin.route('/menu/airing_today')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_airing_today_menu():
    pass


@routing_plugin.route('/menu/calendar_old')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_calendar_menu():
    pass


@routing_plugin.route('/menu/search')
@try_function(ErrorPriority.BLOCKING, fail_menu)
def show_search_menu():
    pass


def play_video_internal(ep_id, file_id, mark_as_watched=True, resume=False):
    # this prevents the spinning wheel
    global plugin_dir
    plugin_dir.success = False
    del plugin_dir

    from shoko_models.v2 import Episode
    ep = Episode(ep_id, build_full_object=True)
    items = [(x.name, x.id) for x in ep]
    selected_id = kodi_utils.show_file_list(items)

    # all of real work is done here
    nakamori_player.play_video(selected_id, ep_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play')
@try_function(ErrorPriority.BLOCKING)
def play_video(ep_id, file_id):
    play_video_internal(ep_id, file_id)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play_without_marking')
def play_video_without_marking(ep_id, file_id):
    play_video_internal(ep_id, file_id, mark_as_watched=False)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/resume')
@try_function(ErrorPriority.BLOCKING)
def resume_video(ep_id, file_id):
    # if we are resuming, then we'll assume that scrobbling and marking are True
    play_video_internal(ep_id, file_id, mark_as_watched=True, resume=True)


def script(script_url):
    return url_for(run_script, pyproxy.quote(pyproxy.quote(script_url)))


@routing_plugin.route('/script/<path:script_url>')
def run_script(script_url):
    global plugin_dir
    plugin_dir.success = False
    del plugin_dir

    xbmc.executebuiltin(pyproxy.unquote(pyproxy.unquote(script_url)))


@try_function(ErrorPriority.BLOCKING)
def main():
    debug.debug_init()
    # stage 1 - check connection
    if not shoko_utils.can_connect():
        script_utils.wizard_connection()
        if not shoko_utils.can_connect():
            raise RuntimeError('Could not connect. Please check your connection settings.')

    # stage 2 - Check server startup status
    if not shoko_utils.get_server_status():
        return

    # stage 3 - auth
    auth = shoko_utils.auth()
    if not auth:
        script_utils.wizard_login()
        auth = shoko_utils.auth()
        if not auth:
            raise RuntimeError('Could not log in. Please check your user settings.')

    routing_plugin.run()
    show_messages()


if __name__ == '__main__':
    main()
