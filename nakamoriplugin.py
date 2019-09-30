# -*- coding: utf-8 -*-
import json
import sys
from distutils.version import LooseVersion
import time
import debug
import error_handler
import nakamori_player
import routing
import xbmcplugin
import xbmc
from error_handler import try_function, show_messages, ErrorPriority, exception
from kodi_models import DirectoryListing, WatchedStatus, ListItem
from nakamori_utils import kodi_utils, shoko_utils, script_utils, model_utils
from proxy.python_version_proxy import python_proxy as pyproxy
from nakamori_utils.globalvars import *
from windows import wizard, information
from setsuzoku import Category, Action, Event

plugin_localize = plugin_addon.getLocalizedString
routing_plugin = routing.Plugin('plugin://plugin.video.nakamori', convert_args=True)
routing_plugin.handle = int(sys.argv[1])
url_for = routing_plugin.url_for
parent_url = sys.argv[0]

# I had to read up on this. Functions have read access to this if they don't declare a plugin_dir
# if you want to do something like del plugin_dir, then you need to do this:
# def play():
#     global plugin_dir
#     del plugin_dir
plugin_dir = DirectoryListing()


def fail_menu():
    global plugin_dir
    plugin_dir.success = False
    del plugin_dir


def finish_menu():
    global plugin_dir
    del plugin_dir


# Order matters on these. In this, it goes try -> route -> show_main_menu
# Python is retarded, as you'd expect the opposite
@routing_plugin.route('/')
@try_function(ErrorPriority.BLOCKING)
def show_main_menu():
    last_call = (int(time.time()) - int(plugin_addon.getSetting('last_call')))
    if last_call > 86400:
        script_utils.log_setsuzoku(Category.PLUGIN, Action.VERSION, plugin_addon.getAddonInfo('version'))
        plugin_addon.setSetting('last_call', '%s' % int(time.time()))

    version = LooseVersion(plugin_addon.getAddonInfo('version'))
    previous_version = plugin_addon.getSetting('version')
    if previous_version == '':
        previous_version = '3.0.9'
    if plugin_addon.getSetting('skip_information') != 'true' and \
            LooseVersion(previous_version) < version:
        fail_menu()
        information.open_information()
        restart_plugin()
        return

    from shoko_models.v2 import Filter
    f = Filter(0, build_full_object=True, parent_menu=parent_url)
    plugin_dir.set_content('tvshows')
    items = []

    bold = True if plugin_addon.getSetting('bold_filters') == 'true' else False
    for item in f:
        if bold:
            item.bold()
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
        plugin_dir.append(item.get_listitem(), item.is_kodi_folder)
    finish_menu()


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
    # { 'Favorites', 'Added Recently v2': 0, 'Airing Today': 1, 'Calendar': 1, 'Seasons': 2, 'Years': 3, 'Tags': 4,
    # 'Unsort': 5, 'Settings' (both): 7, 'Shoko Menu': 8, 'Search': 9, Experiment: 99}

    customize_menu = True if plugin_addon.getSetting('customize_main_menu') == 'true' else False

    if plugin_addon.getSetting('show_favorites') == 'true':
        name = kodi_utils.color(plugin_localize(30211), plugin_addon.getSetting('color_favorites'), customize_menu)
        if plugin_addon.getSetting('bold_favorites') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'airing.png', url_for(show_favorites_menu))
        item.sort_index = 0
        items.append(item)

    if plugin_addon.getSetting('show_bookmark') == 'true':
        name = kodi_utils.color(plugin_localize(30215), plugin_addon.getSetting('color_bookmark'), customize_menu)
        if plugin_addon.getSetting('bold_bookmark') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'airing.png', url_for(show_bookmark_menu))
        item.sort_index = 0
        items.append(item)

    if plugin_addon.getSetting('show_recent2') == 'true':
        name = kodi_utils.color(plugin_localize(30170), plugin_addon.getSetting('color_recent2'), customize_menu)
        if plugin_addon.getSetting('bold_recent2') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'airing.png', url_for(show_added_recently_menu))
        item.sort_index = 0
        items.append(item)

    # TODO airing today
    #if plugin_addon.getSetting('show_airing_today') == 'true':
    #    name = kodi_utils.color(plugin_localize(30211), plugin_addon.getSetting('color_favorites'), color)
    #    item = CustomItem(plugin_localize(30223), 'airing.png', url_for(show_airing_today_menu))
    #    item.sort_index = 1
    #    items.append(item)

    if plugin_addon.getSetting('show_calendar') == 'true':
        name = kodi_utils.color(plugin_localize(30222), plugin_addon.getSetting('color_calendar'), customize_menu)
        if plugin_addon.getSetting('bold_calendar') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        if plugin_addon.getSetting('calendar_basic') == 'true':
            item = CustomItem(name, 'calendar.png', url_for(show_calendar_menu))
            item.is_kodi_folder = True
        else:
            item = CustomItem(name, 'calendar.png', script(script_utils.url_calendar()))
            item.is_kodi_folder = False
        item.sort_index = 12
        items.append(item)

    if plugin_addon.getSetting('show_settings') == 'true':
        name = kodi_utils.color(plugin_localize(30107), plugin_addon.getSetting('color_settings'), customize_menu)
        if plugin_addon.getSetting('bold_settings') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'settings.png', url_for(show_setting_menu))
        item.sort_index = 14
        item.is_kodi_folder = True
        items.append(item)

    if plugin_addon.getSetting('show_shoko') == 'true':
        name = kodi_utils.color(plugin_localize(30115), plugin_addon.getSetting('color_shoko'), customize_menu)
        if plugin_addon.getSetting('bold_shoko') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'settings.png', url_for(show_shoko_menu))
        item.sort_index = 18
        item.is_kodi_folder = True
        items.append(item)

    if plugin_addon.getSetting('show_search') == 'true':
        name = kodi_utils.color(plugin_localize(30221), plugin_addon.getSetting('color_search'), customize_menu)
        if plugin_addon.getSetting('bold_search') == 'true' and customize_menu:
            name = kodi_utils.bold(name)
        item = CustomItem(name, 'search.png', url_for(show_search_menu))
        item.sort_index = 20
        items.append(item)

    if plugin_addon.getSetting('onepunchmen') == 'true':
        item = CustomItem(plugin_localize(30145) + '_tv', 'airing.png', url_for(scrape_all_tvshows))
        item.sort_index = 99
        items.append(item)
        item = CustomItem(plugin_localize(30145) + '_mv', 'airing.png', url_for(scrape_all_movies))
        item.sort_index = 99
        items.append(item)


@routing_plugin.route('/menu-folder/<folderid>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_folder_menu(folderid):
    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.BOOKMARK)
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, str(folderid))
    from shoko_models.v2 import Series
    url = server + '/api/serie/byfolder?id=%s&limit=10000' % folderid
    json_body = pyproxy.get_json(url, True)
    json_node = json.loads(json_body)

    for item in json_node:
        s = Series(item)
        plugin_dir.append(s.get_listitem(), True)
    finish_menu()


@routing_plugin.route('/menu-settings/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_setting_menu():
    script_utils.log_setsuzoku(Category.SHOKO, Action.MENU, Event.SETTINGS)

    from shoko_models.v2 import CustomItem
    xbmcplugin.setPluginCategory(routing_plugin.handle, 'settings')

    name = plugin_localize(30107)
    item = CustomItem(name, 'settings.png', script(script_utils.url_settings()))
    item.sort_index = 14
    item.is_kodi_folder = False
    plugin_dir.append(item.get_listitem(), item.is_kodi_folder)

    name = plugin_localize(30107) + ' Script'
    item = CustomItem(name, 'settings.png', script(script_utils.url_script_settings()))
    item.sort_index = 15
    item.is_kodi_folder = False
    plugin_dir.append(item.get_listitem(), item.is_kodi_folder)

    name = plugin_localize(30107) + ' Service'
    item = CustomItem(name, 'settings.png', script(script_utils.url_service_settings()))
    item.sort_index = 16
    item.is_kodi_folder = False
    plugin_dir.append(item.get_listitem(), item.is_kodi_folder)

    finish_menu()


@routing_plugin.route('/menu-shoko/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_shoko_menu():
    script_utils.log_setsuzoku(Category.SHOKO, Action.MENU, Event.MAIN)

    from shoko_models.v2 import ImportFolders, CustomItem, QueueGeneral, QueueHasher, QueueImages
    xbmcplugin.setPluginCategory(routing_plugin.handle, 'shoko')

    queue_ = QueueHasher()
    plugin_dir.append(queue_.get_listitem(), folder=False)
    queue__ = QueueImages()
    plugin_dir.append(queue__.get_listitem(), folder=False)
    queue___ = QueueGeneral()
    plugin_dir.append(queue___.get_listitem(), folder=False)

    # TODO add folder https://github.com/ShokoAnime/ShokoServer/blob/master/Shoko.Server/API/v2/Modules/Common.cs#L73

    # TODO need to tide this up, until then add as many as you can
    # TODO Lang Fix  <-- not until we know what we have and want we want
    ci = CustomItem('scan_dropfolders', 'search.png', script(script_utils.url_shoko_scandropfolder()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('stats_update', 'search.png', script(script_utils.url_shoko_statusupdate()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('medainfo_update', 'search.png', script(script_utils.url_shoko_mediainfoupdate()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('rescan_unlinked', 'search.png', script(script_utils.url_shoko_rescanunlinked()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('rehash_unlinked', 'search.png', script(script_utils.url_shoko_rehashunlinked()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('rescan_manuallinks', 'search.png', script(script_utils.url_shoko_rescanmanuallinks()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('rehash_manuallinks', 'search.png', script(script_utils.url_shoko_rehashmanuallinks()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem(script_addon.getLocalizedString(30049), 'search.png', script(script_utils.url_shoko_runimport()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem(script_addon.getLocalizedString(30042), 'search.png', script(script_utils.url_shoko_removemissing()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('calendar_refresh', 'search.png', script(script_utils.url_calendar_refresh()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('install webui', 'search.png', script(script_utils.url_install_webui()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('webui stable', 'search.png', script(script_utils.url_stable_webui()))
    plugin_dir.append(ci.get_listitem(), folder=False)
    ci = CustomItem('webui unstable', 'search.png', script(script_utils.url_unstable_webui()))
    plugin_dir.append(ci.get_listitem(), folder=False)

    folders = ImportFolders()
    for folder in folders.items:
        plugin_dir.append(folder.get_listitem())
    finish_menu()


@routing_plugin.route('/filter-<filter_id>/')
@routing_plugin.route('/filter-<parent_id>/filter-<filter_id>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_filter_menu(filter_id=0, parent_id=0):
    plugin_dir.set_content('tvshows')
    plugin_dir.set_cached()  # issue https://github.com/xbmc/xbmc/issues/16206

    from shoko_models.v2 import Filter
    f = Filter(filter_id, build_full_object=True, get_children=True, parent_menu=parent_url)
    xbmcplugin.setPluginCategory(routing_plugin.handle, f.name)
    f.add_sort_methods(routing_plugin.handle)
    for item in f:
        plugin_dir.append(item.get_listitem())

    finish_menu()
    f.apply_default_sorting()


@routing_plugin.route('/filter-<parent_id>/filter-<filter_id>/group-<group_id>/')
def show_group_menu_filtered(group_id, filter_id, parent_id):
    from shoko_models.v2 import Group
    group = Group(group_id, build_full_object=True, get_children=True, filter_id=filter_id, parent_menu=parent_id)
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, group.name)
    group.add_sort_methods(routing_plugin.handle)
    for item in group:
        plugin_dir.append(item.get_listitem())
        xbmc.log('X======???: %s' % item.get_plugin_url(), xbmc.LOGNOTICE)

    finish_menu()
    group.apply_default_sorting()


@routing_plugin.route('/filter-<filter_id>/group-<group_id>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_group_menu(group_id, filter_id):
    show_group_menu_filtered(group_id, filter_id, '')


@routing_plugin.route('/filter-<parent_id>/filter-<filter_id>/group-<group_id>/series-<series_id>/')
@routing_plugin.route('/filter-<filter_id>/group-<group_id>/series-<series_id>/')
@routing_plugin.route('/menu-<menu_name>/series-<series_id>/')
@routing_plugin.route('/menu-search/<query>/series-<series_id>/')
@routing_plugin.route('/menu-azsearch/<query>/series-<series_id>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_series_menu(series_id, filter_id=0, group_id=0, menu_name='', query='', parent_id=0):
    from shoko_models.v2 import Series
    series = Series(series_id, build_full_object=True, get_children=True, force_cache=True, cache_time=10, parent_menu=parent_url)
    xbmcplugin.setPluginCategory(routing_plugin.handle, series.name)
    if len(series.episode_types) > 1:
        plugin_dir.set_content('seasons')
        for item in series.episode_types:
            plugin_dir.append(item.get_listitem())
        finish_menu()
    elif len(series.episode_types) == 1:
        add_episodes(series, series.episode_types[0].episode_type)
    else:
        raise RuntimeError(plugin_localize(30152))


@routing_plugin.route('/filter-<filter_id>/group-<group_id>/series-<series_id>/type-<episode_type>/')
@routing_plugin.route('/menu-<menu_name>/series-<series_id>/type-<episode_type>/')
@routing_plugin.route('/menu-search/<query>/series-<series_id>/type-<episode_type>/')
@routing_plugin.route('/menu-azsearch/<query>/series-<series_id>/type-<episode_type>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_series_episode_types_menu(series_id, episode_type, filter_id=0, group_id=0, menu_name='', query=''):
    from shoko_models.v2 import SeriesTypeList
    types = SeriesTypeList(series_id, episode_type, get_children=True, force_cache=True, cache_time=10, parent_menu=parent_url)
    add_episodes(types, episode_type)


def add_episodes(series, episode_type):
    from kodi_models import ListItem
    plugin_dir.set_content('episodes')
    series.add_sort_methods(routing_plugin.handle)
    select = kodi_utils.get_kodi_setting('videolibrary.tvshowsselectfirstunwatcheditem') > 0 \
             or plugin_addon.getSetting('select_unwatched') == 'true'
    watched_index = 0
    i = 0
    for item in series:
        try:
            if item.get_file() is None:
                continue
            listitem = item.get_listitem()
            assert isinstance(listitem, ListItem)
            if watched_index == i and item.is_watched() == WatchedStatus.WATCHED:
                watched_index += 1
            plugin_dir.append(listitem, False)
            i += 1
        except:
            exception(ErrorPriority.HIGHEST, plugin_localize(30153))

    add_continue_item(series, episode_type, watched_index)

    finish_menu()
    series.apply_default_sorting()
    if select:
        while kodi_utils.is_dialog_active():
            xbmc.sleep(500)
        # the list is definitely not there yet, so try after 0.25s.
        xbmc.sleep(250)
        kodi_utils.move_to_index(watched_index)


def add_continue_item(series, episode_type, watched_index):
    if plugin_addon.getSetting('show_continue') != 'true':
        return
    from shoko_models.v2 import CustomItem
    continue_url = script(script_utils.url_move_to_item(watched_index))

    continue_text = plugin_localize(30053)
    if plugin_addon.getSetting('replace_continue') == 'true':
        if episode_type == "Special":
            eps = series.sizes.watched_specials
            total = series.sizes.total_specials
            if plugin_addon.getSetting('local_only') == 'true':
                total = series.sizes.local_specials
        else:
            eps = series.sizes.watched_episodes
            if plugin_addon.getSetting('local_only') == 'true':
                total = series.sizes.local_episodes
            else:
                total = series.sizes.total_episodes
        continue_text = '[ %s: %s/%s ]' % (episode_type, eps, total)

    continue_item = CustomItem(continue_text, '', continue_url, -1, False)
    continue_item.infolabels['episode'] = 0
    continue_item.infolabels['season'] = 0
    plugin_dir.insert(0, continue_item.get_listitem(), continue_item.is_kodi_folder)


@routing_plugin.route('/menu-added_recently/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_added_recently_menu():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.RECENTLY)
    url = '%s/api/serie/recent' % server
    body = pyproxy.get_json(url, True)
    json_body = json.loads(body)
    plugin_dir.set_content('tvshows')
    from shoko_models.v2 import Series, Episode
    for item in json_body:
        s = Series(item, parent_menu=parent_url)
        plugin_dir.append(s.get_listitem(), True)

    url = '%s/api/ep/recent?level=2' % server
    body = pyproxy.get_json(url, True)
    json_body = json.loads(body)
    for item in json_body:
        e = Episode(item)
        plugin_dir.append(e.get_listitem(), False)

    finish_menu()


@routing_plugin.route('/menu-calendar_old/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_calendar_menu():
    if script_addon.getSetting('custom_source') == 'true':
        from external_calendar import return_only_few
        body = return_only_few(when='', url=str(script_addon.getSetting('custom_url')))
    else:
        import datetime
        when = datetime.datetime.now().strftime('%Y%m%d')
        url = '%s/api/serie/soon?level=2&limit=0&offset=%s&d=%s' % (server, 0, when)
        body = pyproxy.get_json(url, True)
    json_body = json.loads(body)

    plugin_dir.set_content('tvshows')
    from shoko_models.v2 import Series, CustomItem
    processed_dates = []
    for item in json_body['series']:
        s = Series(item)
        if s.date not in processed_dates:
            processed_dates.append(s.date)
            c = CustomItem('[COLOR red]' + str(s.date) + '[/COLOR]', '', '')
            plugin_dir.append(c.get_listitem(), False)
        plugin_dir.append(s.get_listitem(), False)
    finish_menu()


@routing_plugin.route('/menu-filter-unsorted/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_unsorted_menu():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.UNSORT)
    # this is really bad practice, but the unsorted files list is too special
    from shoko_models.v2 import File
    url = server + '/api/file/unsort'
    json_body = pyproxy.get_json(url, True)
    json_node = json.loads(json_body)

    plugin_dir.set_content('episodes')
    for item in json_node:
        f = File(item)
        plugin_dir.append(f.get_listitem(), False)
    finish_menu()


@routing_plugin.route('/menu-bookmark/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_bookmark_menu():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.BOOKMARK)
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, plugin_localize(30215))
    from shoko_models.v2 import Series
    url = server + '/api/serie/bookmark'
    json_body = pyproxy.get_json(url, True)
    json_node = json.loads(json_body)

    for item in json_node.get('series', []):
        s = Series(item, in_bookmark=True, parent_menu=parent_url)
        plugin_dir.append(s.get_listitem(), True)
    finish_menu()


@routing_plugin.route('/menu-favorites/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_favorites_menu():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.FAVORITE)
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, plugin_localize(30211))
    from shoko_models.v2 import Series
    import favorite
    favorite_list = favorite.get_all_favorites()
    try:
        for favorite_serie in favorite_list:
            serie = Series(int(favorite_serie[0]), build_full_object=True, get_children=False, parent_menu=parent_url)
            serie.is_in_favorite()
            plugin_dir.append(serie.get_listitem())
        finish_menu()
    except Exception as ex:
        error_handler.exception(ErrorPriority.HIGHEST, plugin_localize(30151))


@routing_plugin.route('/menu-search/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def show_search_menu(select_query=None, quick_search=False):
    if quick_search:
        plugin_dir.set_cached()  # magic, saved tree structure for search, without it would skip to show_search_menu
        show_search_result_menu(select_query)
        return

    script_utils.log_setsuzoku(Category.PLUGIN, Action.MENU, Event.SEARCH)
    # log(str(xbmc.getInfoLabel('Container.FolderPath')))

    from shoko_models.v2 import CustomItem
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, plugin_localize(30221))

    # Search
    item = CustomItem(kodi_utils.bold(plugin_localize(30224)), 'new-search.png', url_for(new_search, True))
    item.is_kodi_folder = True
    plugin_dir.append(item.get_listitem())

    # quick search
    item = CustomItem(kodi_utils.bold(plugin_localize(30225)), 'search.png', url_for(new_search, False))
    item.is_kodi_folder = False
    plugin_dir.append(item.get_listitem())

    # a-z search (no keyboard)
    item = CustomItem(kodi_utils.bold('A-Z'), 'search.png', url_for(az_search))
    item.is_kodi_folder = False
    plugin_dir.append(item.get_listitem())

    # clear in context menu of each query
    clear_items = (plugin_localize(30110), script_utils.url_clear_search_terms())
    _index = 2
    _index_selected = -1
    import search
    # This is sorted by most recent
    search_history = search.get_search_history()
    for ss in search_history:
        _index += 1
        try:
            query = ss[0]
            if len(query) == 0:
                continue
            item = CustomItem(query, 'search.png', url_for(show_search_result_menu, query))

            remove_item = (plugin_localize(30204), script_utils.url_remove_search_term(query))
            item.set_context_menu_items([remove_item, clear_items])

            list_item = item.get_listitem()
            if select_query == query:
                list_item.select(True)
                _index_selected = _index
            plugin_dir.append(list_item)
        except:
            error_handler.exception(ErrorPriority.HIGHEST, plugin_localize(30151))

    # add clear all for more than 10 items, no one wants to clear them by hand
    if len(search_history) > 10:
        item = CustomItem(plugin_localize(30110), 'search.png', script_utils.url_clear_search_terms())
        plugin_dir.append(item.get_listitem())

    finish_menu()

    if _index_selected != -1:
        script_utils.move_to_item_and_enter(_index_selected)


@routing_plugin.route('/menu-search/<path:query>/')
def show_search_result_menu(query):
    plugin_dir.set_cached()
    search_url = server + '/api/search'
    groups = query_search_and_return_groups(search_url, query)
    from shoko_models.v2 import Series
    for item in groups.get('series', []):
        series = Series(item, build_full_object=True, get_children=True, parent_menu=parent_url)
        plugin_dir.append(series.get_listitem())
    finish_menu()


def query_search_and_return_groups(search_url, query):
    search_url = model_utils.add_default_parameters(search_url, 0, 1)
    search_url = pyproxy.set_parameter(search_url, 'query', query)
    search_url = pyproxy.set_parameter(search_url, 'tags', 2)
    search_url = pyproxy.set_parameter(search_url, 'limit', plugin_addon.getSetting('maxlimit'))
    search_url = pyproxy.set_parameter(search_url, 'limit_tag', plugin_addon.getSetting('maxlimit_tag'))
    json_body = json.loads(pyproxy.get_json(search_url))
    groups = json_body['groups'][0]
    if json_body.get('size', 0) == 0:
        # Show message about no results
        kodi_utils.message_box(plugin_localize(30180), plugin_localize(30181))
        # draw search menu instead of deleting menu
        show_search_menu()
        return
    from shoko_models.v2 import Group
    plugin_dir.set_content('tvshows')
    xbmcplugin.setPluginCategory(routing_plugin.handle, query)
    Group(0).add_sort_methods(routing_plugin.handle)
    return groups


@routing_plugin.route('/menu-azsearch/')
@routing_plugin.route('/menu-azsearch/<character>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def az_search(character=''):
    from shoko_models.v2 import CustomItem, Series
    from string import ascii_lowercase

    if character == '':
        for c in ascii_lowercase:
            item = CustomItem('%s%s' % (character, c), 'search.png', url_for(az_search, '%s%s' % (character, c)))
            item.is_kodi_folder = False
            plugin_dir.append(item.get_listitem())

    elif character != '':
        # az_search_character(character)
        search_url = server + '/api/serie/startswith'
        groups = query_search_and_return_groups(search_url, character)
        character_list = []
        items = []

        for item in groups.get('series', []):
            series = Series(item, parent_menu=parent_url)
            series.name = series.match
            series.sort_index = 10
            items.append(series)
            _index = len(character)
            if len(series.match) > _index:
                _new_char = pyproxy.decode(series.match[_index].encode('utf-8').lower())
                if _new_char not in character_list:
                    character_list.append(_new_char)

        if len(character_list) > 1:
            for c in character_list:
                item = CustomItem('%s%s' % (character, c), 'search.png', url_for(az_search, '%s%s' % (character, c)))
                item.is_kodi_folder = False
                item.sort_index = 0
                items.append(item)

        if any(x.sort_index != 0 for x in items):
            items.sort(key=lambda a: (a.sort_index, a.name))
        for item in items:
            plugin_dir.append(item.get_listitem())

    finish_menu()


@routing_plugin.route('/dialog/search/<save>/')
@try_function(ErrorPriority.BLOCKING, except_func=fail_menu)
def new_search(save):
    x = str(xbmc.getInfoLabel('Container.FolderPath')).lower()  # just in case, future proof

    y = ''
    query = ''
    if 'nakamori/dialog/search/' in x:
        y = 'search'
    elif 'nakamori/menu-search/' in x:
        import re
        try:
            y = re.search("(^plugin://plugin.video.nakamori/menu-search/)(.+)(/)", x).group(2)
            query = y
        except:
            y = 'search'
    elif 'nakamori/menu/series/' in x:  # returning, but cache should bypass this direction
        y = 'series'

    if len(y) != 0:
        if query == '':
            query = kodi_utils.search_box()
        if query != '':
            if save:
                import search
                if search.check_in_database(query):
                    search.remove_search_history(query)
                search.add_search_history(query)

            if len(query) > 0:
                show_search_result_menu(query)
        else:
            show_search_menu()
    else:
        xbmc.log('new_search len(y)=0, path: %s' % x, xbmc.LOGNOTICE)  # log this because it should be possible
        show_search_menu()


# region Play files

class PlaybackType(object):
    NORMAL = 'Normal'
    DIRECT = 'Direct'
    TRANSCODE = 'Transcode'


def play_video_internal(playbacktype, ep_id, file_id, mark_as_watched=True, resume=False, party_mode=False):
    # this prevents the spinning wheel
    # fail_menu()  <--- this breaks serResolvedUrl

    if ep_id > 0 and file_id == 0:
        from shoko_models.v2 import Episode
        ep = Episode(ep_id, build_full_object=True)
        # follow pick_file setting
        if plugin_addon.getSetting('pick_file') == 'true':
            items = [(x.name, x.id) for x in ep]
            selected_id = kodi_utils.show_file_list(items)
        else:
            selected_id = ep.get_file().id
    else:
        selected_id = file_id

    # all of real work is done here
    if playbacktype == PlaybackType.NORMAL:
        nakamori_player.play_video(selected_id, ep_id, mark_as_watched, resume, party_mode=party_mode)
    elif playbacktype == PlaybackType.DIRECT:
        nakamori_player.direct_play_video(selected_id, ep_id, mark_as_watched, resume)
    elif playbacktype == PlaybackType.TRANSCODE:
        nakamori_player.transcode_play_video(selected_id, ep_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/transcode/')
@try_function(ErrorPriority.BLOCKING)
def transcode_play_video(ep_id, file_id, mark_as_watched=True, resume=False):
    play_video_internal(PlaybackType.TRANSCODE, ep_id, file_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/directplay/')
@try_function(ErrorPriority.BLOCKING)
def direct_play_video(ep_id, file_id=0, mark_as_watched=True, resume=False):
    play_video_internal(PlaybackType.DIRECT, ep_id, file_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play/')
def play_video(ep_id, file_id):
    play_video_internal(PlaybackType.NORMAL, ep_id, file_id)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play/party/')
def play_video_in_partymode(ep_id, file_id):
    play_video_internal(PlaybackType.NORMAL, ep_id, file_id, party_mode=True)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play_without_marking/')
def play_video_without_marking(ep_id, file_id):
    play_video_internal(PlaybackType.NORMAL, ep_id, file_id, mark_as_watched=False)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/resume/')
@try_function(ErrorPriority.BLOCKING)
def resume_video(ep_id, file_id):
    # if we are resuming, then we'll assume that scrobbling and marking are True
    play_video_internal(PlaybackType.NORMAL, ep_id, file_id, mark_as_watched=True, resume=True)


# endregion


def script(script_url):
    return url_for(run_script, script_url)


@routing_plugin.route('/script/<path:script_url>')
def run_script(script_url):
    global plugin_dir
    plugin_dir.success = False
    del plugin_dir

    xbmc.executebuiltin(script_url)


def restart_plugin():
    script_utils.arbiter(0, 'RunAddon("plugin.video.nakamori")')


# region TVShows VideoLibrary

@routing_plugin.route('/tvshows/')
def scrape_all_tvshows():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.LIBRARY, Event.TVSHOW)
    scrape_series('tvshows')


@routing_plugin.route('/movies/')
def scrape_all_movies():
    script_utils.log_setsuzoku(Category.PLUGIN, Action.LIBRARY, Event.MOVIE)
    scrape_series('movies', tvshows=False)


def scrape_series(content_type, tvshows=True):
    from shoko_models.v2 import Series
    plugin_dir.set_content(content_type)
    url = server + '/api/serie'
    url = model_utils.add_default_parameters(url, 0, 0)
    body = pyproxy.get_json(url)
    json_node = json.loads(body)
    # it's a list of series nodes
    for node in json_node:
        is_folder = True
        series = Series(node, compute_hash=True, seiyuu_pic=True)
        if tvshows:
            if series.is_movie:
                continue
            url = url_for(scrape_tvshows, series.id)
        else:
            if not series.is_movie:
                continue
            series = Series(node, build_full_object=True, get_children=True, compute_hash=True, seiyuu_pic=True)
            m_id = 0
            for m in series.items:
                if m.item_type == 'movie':
                    m_id = m.id
                    break
            if m_id == 0:
                continue
            url = 'plugin://plugin.video.nakamori/movies/%s/play/' % m_id
            is_folder = False

        li = series.get_listitem(url, disable_coloring=True)

        if not plugin_dir.append(li, is_folder):
            error_handler.exception(ErrorPriority.HIGHEST, 'Unable to scan series')
            break


@routing_plugin.route('/tvshows/<series_id>/')
@routing_plugin.route('/tvshows/<series_id>/ep/<ep_id>/')  # this one is for refresh
@try_function(ErrorPriority.BLOCKING)
def scrape_tvshows(series_id, ep_id=0):
    # handle refresh, check, etc
    if 'kodi-action' in routing_plugin.args:
        if routing_plugin.args['kodi-action'] == 'check_exists':
            # TODO actually check it
            xbmcplugin.setResolvedUrl(routing_plugin.handle, True, ListItem())
        if routing_plugin.args['kodi-action'] == 'refresh_info':
            # TODO Hash the url and reuse it
            scrape_episodes('episodes', series_id)
        return

    # List series items
    scrape_episodes('episodes', series_id)
    # finish_menu is only needed if you need to do something after it


@routing_plugin.route('/movies/<series_id>/')
@routing_plugin.route('/movies/<series_id>/ep/<ep_id>/')  # this one is for refresh
@try_function(ErrorPriority.BLOCKING)
def scrape_movies(series_id, ep_id=0):
    # handle refresh, check, etc
    if 'kodi-action' in routing_plugin.args:
        if routing_plugin.args['kodi-action'] == 'check_exists':
            # TODO actually check it
            xbmcplugin.setResolvedUrl(routing_plugin.handle, True, ListItem())
        if routing_plugin.args['kodi-action'] == 'refresh_info':
            # TODO Hash the url and reuse it
            scrape_episodes('episodes', series_id)
        return

    # List series items
    scrape_episodes('episodes', series_id)


def scrape_episodes(episodes_label, series_id):
    from shoko_models.v2 import Series
    plugin_dir.set_content(episodes_label)
    # get series info
    series = Series(series_id, build_full_object=True, get_children=True, compute_hash=True, seiyuu_pic=True)
    if series.is_movie:
        return
    # series iterates Episodes
    for i in series:
        # filter out anything that is not important
        if i.episode_type.lower() not in ('episode', 'special', 'ova'):
            continue
        # url = url_for(play_episode, i.id)
        url = 'plugin://plugin.video.nakamori/tvshows/%s/ep/%s/play/' % (series.id, i.id)

        li = i.get_listitem(url)
        li.setProperty('IsPlayable', 'true')
        if not plugin_dir.append(li, folder=False, total_items=len(series.items)):
            error_handler.exception(ErrorPriority.HIGHEST, 'Unable to scan episode')
            break


@routing_plugin.route('/tvshows/<ep_id>/play/')
@routing_plugin.route('/tvshows/<series_id>/ep/<ep_id>/play/')
@routing_plugin.route('/movies/<ep_id>/play/')
@try_function(ErrorPriority.BLOCKING)
def play_episode(ep_id, series_id=0):
    play_video_internal(PlaybackType.NORMAL, ep_id, file_id=0, mark_as_watched=False)


# endregion


@try_function(ErrorPriority.BLOCKING)
def main():
    debug.debug_init()

    # stage 0 - everything before connecting
    kodi_utils.get_device_id()

    # stage 1 - check connection
    if not shoko_utils.can_connect():
        fail_menu()
        kodi_utils.message_box(plugin_localize(30159), plugin_localize(30154))
        if wizard.open_connection_wizard():
            restart_plugin()
            return
        if not shoko_utils.can_connect():
            raise RuntimeError(plugin_localize(30155))

    # stage 2 - Check server startup status
    if not shoko_utils.get_server_status():
        return

    # stage 3 - auth
    auth = shoko_utils.auth()
    if not auth:
        fail_menu()
        kodi_utils.message_box(plugin_localize(30156), plugin_localize(30157))
        if wizard.open_login_wizard():
            restart_plugin()
            return
        auth = shoko_utils.auth()
        if not auth:
            raise RuntimeError(plugin_localize(30158))

    routing_plugin.run()


if __name__ == '__main__':
    main()
    show_messages()
