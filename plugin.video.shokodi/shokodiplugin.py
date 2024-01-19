import json
import sys

import shokodiplayer
from lib.utils.globalvars import *
from lib import debug, error_handler
from lib.error_handler import show_messages, ErrorPriority, exception, Try
from lib.proxy.kodi import kodi_proxy
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.python import proxy as pyproxy
from lib.proxy.kodi.directory_listing import DirectoryListing
from lib.utils import model_utils
from lib.shoko import connection_handler
from plugin_routes import PluginRoutes
from script_routes import ScriptRoutes

plugin_localize = plugin_addon.getLocalizedString
url_for = plugin_router.url_for

resume_arg = False
if len(sys.argv) > 2:
    for arg in sys.argv:
        parts = arg.split(':')
        if len(parts) < 2: continue
        if not parts[0].strip().lower() == 'resume': continue
        if not parts[1].strip().lower() == 'true': continue
        resume_arg = True
        break


class ShokodiPlugin(PluginRoutes):
    def __init__(self):
        self.plugin_dir = DirectoryListing()

    def fail_menu(self):
        self.plugin_dir.success = False
        self.plugin_dir.finish()

    def finish_menu(self):
        self.plugin_dir.finish()

    @Try(error_priority=ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_main_menu(self):
        from lib.shoko.v2 import Filter
        f = Filter(0, build_full_object=True)
        self.plugin_dir.set_content('tvshows')
        items = []

        for item in f:
            items.append(item)
        # apply settings for main menu
        items[:] = [x for x in items if not self.is_main_menu_item_enabled(x)]

        self.add_extra_main_menu_items(items)

        # sort the filters
        try:
            # if they are all zero, preserve server sorting
            if any(x.sort_index != 0 for x in items):
                items.sort(key=lambda a: (a.sort_index, a.name))
        except:
            error_handler.exception(ErrorPriority.HIGH)
        for item in items:
            self.plugin_dir.append(item.get_listitem(), item.is_kodi_folder)

        self.finish_menu()

    @staticmethod
    def is_main_menu_item_enabled(item):
        """
    
        :param item:
        :type item: Filter
        :return:
        """
        # This only has one at the moment, but we may add the ability for more later
        if item.name == 'Unsorted Files' and not plugin_addon.getSetting('show_unsort') == 'true':
            return False

    def add_extra_main_menu_items(self, items):
        """
        Add items like search, calendar, etc
        :param items:
        :return:
        """
        from lib.shoko.v2 import CustomItem
        # { 'Seasons': 2, 'Years': 3, 'Tags': 4,
        # 'Unsort': 5, 'Settings' (both): 7, 'Shoko Menu': 8, 'Search': 9, Experiment: 99}

        if plugin_addon.getSetting('show_shoko') == 'true':
            item = CustomItem(plugin_localize(30115), 'settings.png',
                              script_router.url_for(ScriptRoutes.shoko_menu))
            item.sort_index = 8
            item.is_kodi_folder = False
            items.append(item)

        if plugin_addon.getSetting('show_search') == 'true':
            item = CustomItem(plugin_localize(30221), 'search.png', url_for(self.show_search_menu))
            item.sort_index = 9
            items.append(item)

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_filter_menu(self, filter_id):
        from lib.shoko.v2 import Filter
        f = Filter(filter_id, build_full_object=True, get_children=True)
        self.plugin_dir.set_content('tvshows')
        self.plugin_dir.set_cached()
        f.add_sort_methods(plugin_router.handle)
        for item in f:
            self.plugin_dir.append(item.get_listitem())

        self.finish_menu()
        f.apply_default_sorting()

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_group_menu(self, group_id, filter_id):
        from lib.shoko.v2 import Group
        group = Group(group_id, build_full_object=True, get_children=True, filter_id=filter_id)
        self.plugin_dir.set_content('tvshows')
        group.add_sort_methods(plugin_router.handle)
        for item in group:
            self.plugin_dir.append(item.get_listitem())

        self.finish_menu()
        group.apply_default_sorting()

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_series_menu(self, series_id):
        from lib.shoko.v2 import Series
        series = Series(series_id, build_full_object=True, get_children=True)

        if len(series.episode_types) > 1:
            self.plugin_dir.set_content('seasons')
            # type listing
            for item in series.episode_types:
                self.plugin_dir.append(item.get_listitem())
            self.finish_menu()
        elif len(series.episode_types) == 1:
            self.add_episodes(series, series.episode_types[0].episode_type)
        else:
            raise RuntimeError(plugin_localize(30152))

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_series_episode_types_menu(self, series_id, episode_type):
        from lib.shoko.v2 import SeriesTypeList
        types = SeriesTypeList(series_id, episode_type, get_children=True)
        self.add_episodes(types, episode_type)

    def add_episodes(self, series, episode_type):
        self.plugin_dir.set_content('episodes')
        series.add_sort_methods(plugin_router.handle)
        select = kodi_proxy.Util.get_kodi_setting('videolibrary.tvshowsselectfirstunwatcheditem') > 0 \
                 or plugin_addon.getSetting('select_unwatched') == 'true'
        watched_index = 0
        i = 0
        for item in series:
            try:
                if item.get_file() is None:
                    continue
                listitem = item.get_listitem()
                if watched_index == i and item.is_watched() == WatchedStatus.WATCHED:
                    watched_index += 1
                self.plugin_dir.append(listitem, False)
                i += 1
            except:
                exception(ErrorPriority.HIGHEST, plugin_localize(30153))

        self.add_continue_item(series, episode_type, watched_index)

        self.finish_menu()
        series.apply_default_sorting()
        if select:
            while kodi_proxy.Util.is_dialog_active():
                kodi_proxy.sleep(500)
            # the list is definitely not there yet, so try after 0.25s.
            kodi_proxy.sleep(250)
            kodi_proxy.Util.move_to_index(watched_index)

    def add_continue_item(self, series, episode_type, watched_index):
        if plugin_addon.getSetting('show_continue') != 'true':
            return
        from lib.shoko.v2 import CustomItem
        continue_url = plugin_router.url_for(PluginRoutes.run_script,
                                             script_router.url_for(ScriptRoutes.move_to_index, watched_index))

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
        self.plugin_dir.insert(0, continue_item.get_listitem(), continue_item.is_kodi_folder)

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_unsorted_menu(self):
        # this is really bad practice, but the unsorted files list is too special
        from lib.shoko.v2 import File
        url = server + '/api/file/unsort'
        json_body = pyproxy.get_json(url)
        json_node = json.loads(json_body)

        self.plugin_dir.set_content('episodes')
        for item in json_node:
            f = File(item)
            self.plugin_dir.append(f.get_listitem(), False)
        self.finish_menu()

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def show_search_menu(self):
        # search for new
        # quick search
        # clear search in context_menu
        from lib.shoko.v2 import CustomItem
        self.plugin_dir.set_content('videos')

        clear_items = (plugin_localize(30110), script_router.url_for(ScriptRoutes.clear_search))

        # Search
        item = CustomItem(plugin_localize(30224), 'new-search.png', url_for(self.new_search, True))
        item.is_kodi_folder = False
        item.set_context_menu_items([clear_items])
        self.plugin_dir.append(item.get_listitem())

        # quick search
        # TODO Setting for this, etc
        item = CustomItem(plugin_localize(30225), 'search.png', url_for(self.new_search, False))
        item.is_kodi_folder = False
        item.set_context_menu_items([clear_items])
        self.plugin_dir.append(item.get_listitem())

        from lib import search
        # This is sorted by most recent
        search_history = search.get_search_history()
        for ss in search_history:
            try:
                query = ss[0]
                if len(query) == 0:
                    continue
                item = CustomItem(query, 'search.png', url_for(self.show_search_result_menu, query))

                remove_item = (
                plugin_localize(30204), script_router.url_for(ScriptRoutes.remove_search_term, query))
                item.set_context_menu_items([remove_item, clear_items])

                self.plugin_dir.append(item.get_listitem())
            except:
                error_handler.exception(ErrorPriority.HIGHEST, plugin_localize(30151))

        # add clear all for more than 10 items, no one wants to clear them by hand
        if len(search_history) > 10:
            item = CustomItem(plugin_localize(30110), 'search.png',
                              script_router.url_for(ScriptRoutes.clear_search))
            self.plugin_dir.append(item.get_listitem())
        self.finish_menu()

    @Try(ErrorPriority.BLOCKING, except_func=fail_menu)
    def new_search(self, save):
        query = kodi_proxy.Dialog.text_input(plugin_localize(30026))

        if save:
            from lib import search
            if search.check_in_database(query):
                search.remove_search_history(query)
            search.add_search_history(query)

        if len(query) > 0:
            self.show_search_result_menu(pyproxy.quote(pyproxy.quote(query)))

    def show_search_result_menu(self, query):
        search_url = server + '/api/search'
        search_url = model_utils.add_default_parameters(search_url, 0, 1)
        search_url = pyproxy.set_parameter(search_url, 'query', query)
        search_url = pyproxy.set_parameter(search_url, 'tags', 2)
        search_url = pyproxy.set_parameter(search_url, 'limit', plugin_addon.getSetting('maxlimit'))
        search_url = pyproxy.set_parameter(search_url, 'limit_tag', plugin_addon.getSetting('maxlimit_tag'))
        json_body = json.loads(pyproxy.get_json(search_url))
        groups = json_body['groups'][0]
        if json_body.get('size', 0) == 0:
            # Show message about no results
            kodi_proxy.Dialog.ok(plugin_localize(30180), plugin_localize(30181))
            # draw search menu instead of deleting menu
            self.show_search_menu()
            return

        self.plugin_dir.set_content('tvshows')
        from lib.shoko.v2 import Group, Series
        Group(0).add_sort_methods(plugin_router.handle)
        for item in groups.get('series', []):
            series = Series(item, build_full_object=True, get_children=True)
            self.plugin_dir.append(series.get_listitem())
        self.finish_menu()

    def play_video_internal(self, ep_id, file_id, mark_as_watched=True, resume=False):
        # this prevents the spinning wheel
        self.fail_menu()

        if ep_id > 0 and file_id == 0:
            from lib.shoko.v2 import Episode
            ep = Episode(ep_id, build_full_object=True)
            # follow pick_file setting
            if plugin_addon.getSetting('pick_file') == 'true':
                items = [(x.name, x.id) for x in ep]
                selected_id = model_utils.show_file_list(items)
            else:
                selected_id = ep.get_file().id
        else:
            selected_id = file_id

        # all of real work is done here
        shokodiplayer.play_video(file_id=selected_id, ep_id=ep_id, mark_as_watched=mark_as_watched, resume=resume)
        while kodi_proxy.Util.is_dialog_active():
            kodi_proxy.sleep(500)

    def play_video(self, ep_id=0, file_id=0):
        self.play_video_internal(ep_id, file_id, resume=resume_arg)

    def play_video_without_marking(self, ep_id=0, file_id=0):
        self.play_video_internal(ep_id, file_id, mark_as_watched=False)

    @Try(ErrorPriority.BLOCKING)
    def resume_video(self, ep_id=0, file_id=0):
        # if we are resuming, then we'll assume that scrobbling and marking are True
        self.play_video_internal(ep_id, file_id, mark_as_watched=True, resume=True)

    def run_script(self, script_url):
        self.fail_menu()
        kodi_proxy.executebuiltin(script_url)

    @staticmethod
    def restart_plugin():
        kodi_proxy.executebuiltin(script_router.url_for(ScriptRoutes.arbiter, wait=0,
                                                        arg='RunAddon("plugin.video.shokodi")'))

    @Try(ErrorPriority.BLOCKING)
    def main(self):
        debug.debug_init()
        # stage 1 - check connection
        if not connection_handler.can_connect():
            self.fail_menu()
            kodi_proxy.Dialog.ok(plugin_localize(30159), plugin_localize(30154))
            from lib.windows import wizard
            if wizard.open_connection_wizard():
                self.restart_plugin()
                return
            if not connection_handler.can_connect():
                raise RuntimeError(plugin_localize(30155))

        # stage 2 - Check server startup status
        if not connection_handler.get_server_status():
            return

        # stage 3 - auth
        auth = connection_handler.auth()
        if not auth:
            self.fail_menu()
            kodi_proxy.Dialog.ok(plugin_localize(30156), plugin_localize(30157))
            from lib.windows import wizard
            if wizard.open_login_wizard():
                self.restart_plugin()
                return
            auth = connection_handler.auth()
            if not auth:
                raise RuntimeError(plugin_localize(30158))

        plugin_router.run()
        debug.print_profiler()


if __name__ == '__main__':
    plugin = ShokodiPlugin()
    plugin_router.instance = plugin
    plugin.main()
    show_messages()
