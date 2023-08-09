from lib.utils.globalvars import *


class PluginRoutes(object):
    @plugin_router.route('/')
    def show_main_menu(self):
        pass

    @plugin_router.route('/menu/filter/<filter_id>/')
    def show_filter_menu(self, filter_id):
        pass

    @plugin_router.route('/menu/group/<group_id>/filterby/<filter_id>/')
    def show_group_menu(self, group_id, filter_id):
        pass

    @plugin_router.route('/menu/series/<series_id>/')
    def show_series_menu(self, series_id):
        pass

    @plugin_router.route('/menu/series/<series_id>/type/<episode_type>/')
    def show_series_episode_types_menu(self, series_id, episode_type):
        pass

    @plugin_router.route('/menu/filter/unsorted')
    def show_unsorted_menu(self):
        pass

    @plugin_router.route('/menu/search')
    def show_search_menu(self):
        pass

    @plugin_router.route('/dialog/search/<save>')
    def new_search(self, save):
        pass

    @plugin_router.route('/menu/search/<path:query>')
    def show_search_result_menu(self, query):
        pass

    @plugin_router.route('/episode/<ep_id>/file/<file_id>/play')
    def play_video(self, ep_id=0, file_id=0):
        pass

    @plugin_router.route('/episode/<ep_id>/file/<file_id>/play_without_marking')
    def play_video_without_marking(self, ep_id=0, file_id=0):
        pass

    @plugin_router.route('/episode/<ep_id>/file/<file_id>/resume')
    def resume_video(self, ep_id=0, file_id=0):
        pass

    @plugin_router.route('/script/<path:script_url>')
    def run_script(self, script_url):
        pass
