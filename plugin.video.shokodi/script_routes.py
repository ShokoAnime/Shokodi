from lib.utils.globalvars import script_router


class ScriptRoutes(object):
    @script_router.route('/')
    def root(self):
        pass

    @script_router.route('/arbiter/<wait>/<path:arg>')
    def arbiter(self, wait, arg):
        pass

    @script_router.route('/dialog/wizard/connection')
    def wizard_connection(self):
        pass

    @script_router.route('/dialog/wizard/login')
    def wizard_login(self):
        pass

    @script_router.route('/dialog/shoko')
    def shoko_menu(self):
        pass

    @script_router.route('/search/remove/<path:query>')
    def remove_search_term(self, query):
        pass

    @script_router.route('/search/clear')
    def clear_search(self):
        pass

    @script_router.route('/kodi/clear_image_cache')
    def clear_image_cache(self):
        pass

    @script_router.route('/kodi/clear_listitem_cache')
    def clear_listitem_cache(self):
        pass

    @script_router.route('/refresh')
    def refresh(self):
        pass

    @script_router.route('/dialog/vote_series/<series_id>/')
    def show_series_vote_dialog(self, series_id):
        pass

    @script_router.route('/dialog/vote_episode/<ep_id>/')
    def show_episode_vote_dialog(self, ep_id):
        pass

    @script_router.route('/series/<series_id>/vote')
    def vote_for_series(self, series_id):
        pass

    @script_router.route('/episode/<ep_id>/vote')
    def vote_for_episode(self, ep_id):
        pass

    @script_router.route('/ep/<ep_id>/file_list')
    def file_list(self, ep_id):
        pass

    @script_router.route('/file/<file_id>/rescan')
    def rescan_file(self, file_id):
        pass

    @script_router.route('/file/<file_id>/rehash')
    def rehash_file(self, file_id):
        pass

    @script_router.route('/episode/<ep_id>/set_watched/<watched>')
    def set_episode_watched_status(self, ep_id, watched):
        pass

    @script_router.route('/series/<series_id>/set_watched/<watched>')
    def set_series_watched_status(self, series_id, watched):
        pass

    @script_router.route('/group/<group_id>/set_watched/<watched>')
    def set_group_watched_status(self, group_id, watched):
        pass

    @script_router.route('/menu/episode/move_to_item/<index>/')
    def move_to_index(self, index):
        pass
