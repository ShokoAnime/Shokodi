#!/usr/bin/env python
# -*- coding: utf-8 -*-
import lib.utils.model_utils
from lib.utils.globalvars import *

import nakamoriplayer
from lib import debug, search
from lib.error_handler import spam, ErrorPriority, Try, show_messages
from lib.proxy.kodi import kodi_proxy
from lib.proxy.python import proxy as pyproxy
from lib.shoko import connection_handler
from script_routes import ScriptRoutes


class NakamoriScript(ScriptRoutes):
    def root(self):
        items = [
            (plugin_addon.getLocalizedString(30025), (self.wizard_connection, [])),
            (plugin_addon.getLocalizedString(30043), (self.wizard_login, [])),
        ]

        options = []
        for item in items:
            options.append(item[0])

        result = kodi_proxy.Dialog.context(options)
        if result >= 0:
            action, args = items[result][1]
            action(*args)

    @Try(ErrorPriority.BLOCKING)
    def arbiter(self, wait, arg):
        spam('arbiting', 'wait:', wait, 'arg:', arg)
        if wait is None or arg is None:
            raise RuntimeError('Arbiter received no parameters')
        kodi_proxy.sleep(wait)
        kodi_proxy.executebuiltin(arg)

    def wizard_connection(self):
        from lib.windows import wizard
        wizard.open_connection_wizard()

    def wizard_login(self):
        from lib.windows import wizard
        wizard.open_login_wizard()

    @Try(ErrorPriority.BLOCKING)
    def shoko_menu(self):
        # TODO add things
        # Remove Missing
        # Import Folders?
        # various other actions
        items = [
            (plugin_addon.getLocalizedString(30049), connection_handler.run_import, []),
            (plugin_addon.getLocalizedString(30042), connection_handler.remove_missing_files, [])
        ]

        options = []
        for item in items:
            options.append(item[0])

        result = kodi_proxy.Dialog.context(options)
        if result >= 0:
            action, args = items[result][1]
            action(*args)

    def remove_search_term(self, query):
        search.remove_search_history(query)
        kodi_proxy.Dialog.refresh()

    def clear_search(self):
        search.remove_search_history()
        kodi_proxy.Dialog.refresh()

    def clear_image_cache(self):
        kodi_proxy.Util.clear_image_cache()

    def clear_listitem_cache(self):
        kodi_proxy.Util.clear_listitem_cache()

    def refresh(self):
        kodi_proxy.Dialog.refresh()

    @Try(ErrorPriority.BLOCKING)
    def show_series_vote_dialog(self, series_id):
        pass

    @Try(ErrorPriority.BLOCKING)
    def show_episode_vote_dialog(self, ep_id):
        pass

    @Try(ErrorPriority.BLOCKING)
    def vote_for_series(self, series_id):
        from lib.shoko.v2 import Series
        series = Series(series_id)
        suggest_rating = ''
        if plugin_addon.getSetting('suggest_series_vote') == 'true':
            if plugin_addon.getSetting('suggest_series_vote_all_eps') == 'true' and not series.all_episodes_voted:
                kodi_proxy.Dialog.ok('', plugin_addon.getLocalizedString(30353))
                return
            suggest_rating = ' [ %s ]' % series.suggest_rating_based_on_episode_rating

        vote_list = ['Don\'t Vote' + suggest_rating, '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
        my_vote = kodi_proxy.Dialog.select(plugin_addon.getLocalizedString(30023), vote_list)
        if my_vote < 1:
            return
        my_vote = pyproxy.safe_int(vote_list[my_vote])
        if my_vote < 1:
            return
        series.vote(my_vote)

    @Try(ErrorPriority.BLOCKING)
    def vote_for_episode(self, ep_id):
        from lib.shoko.v2 import Episode
        vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
        my_vote = kodi_proxy.Dialog.select(plugin_addon.getLocalizedString(30023), vote_list)
        if my_vote < 1:
            return
        my_vote = pyproxy.safe_int(vote_list[my_vote])
        if my_vote < 1:
            return
        ep = Episode(ep_id)
        ep.vote(my_vote)

    @Try(ErrorPriority.BLOCKING)
    def file_list(self, ep_id):
        from lib.shoko.v2 import Episode
        ep = Episode(ep_id, build_full_object=True)
        items = [(x.name, x.id) for x in ep]
        selected_id = lib.utils.model_utils.show_file_list(items)
        nakamoriplayer.play_video(file_id=selected_id, ep_id=ep_id)

    @Try(ErrorPriority.BLOCKING)
    def rescan_file(self, file_id):
        from lib.shoko.v2 import File
        f = File(file_id)
        f.rescan()

    @Try(ErrorPriority.BLOCKING)
    def rehash_file(self, file_id):
        from lib.shoko.v2 import File
        f = File(file_id)
        f.rehash()

    @Try(ErrorPriority.HIGH, 'Error Setting Watched Status')
    def set_episode_watched_status(self, ep_id, watched):
        from lib.shoko.v2 import Episode
        ep = Episode(ep_id)
        ep.set_watched_status(watched)
        kodi_proxy.Dialog.refresh()

    @Try(ErrorPriority.HIGH, 'Error Setting Watched Status')
    def set_series_watched_status(self, series_id, watched):
        from lib.shoko.v2 import Series
        series = Series(series_id)
        series.set_watched_status(watched)
        kodi_proxy.Dialog.refresh()

    def set_group_watched_status(self, group_id, watched):
        from lib.shoko.v2 import Group
        group = Group(group_id)
        group.set_watched_status(watched)
        kodi_proxy.Dialog.refresh()

    def move_to_index(self, index):
        kodi_proxy.Util.move_to_index(index)

    @Try(ErrorPriority.BLOCKING)
    def main(self):
        script_router.run()


if __name__ == '__main__':
    debug.debug_init()
    script = NakamoriScript()
    script_router.instance = script
    script.main()
    show_messages()
