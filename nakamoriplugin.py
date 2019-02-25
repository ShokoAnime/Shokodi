import routing
from kodi_models.kodi_models import DirectoryListing
from lib import debug

routing_plugin = routing.Plugin('plugin://plugin.video.nakamori')


@routing_plugin.route('/')
def main():
    # start debugging, show main menu, first run wizard

    show_main_menu()


@routing_plugin.route('/menu/main')
def show_main_menu():
    show_filter_menu(0)


@routing_plugin.route('/menu/filter/<filter_id>')
def show_filter_menu(filter_id):
    from shoko_models.v2 import Filter
    filter = Filter(filter_id, build_full_object=True)
    dir = DirectoryListing('tvshows')
    for item in filter:
        dir.append(item.get_listitem())


@routing_plugin.route('/menu/group/<group_id>/filterby/<filter_id>')
def show_group_menu(group_id, filter_id):
    from shoko_models.v2 import Group
    group = Group(group_id, build_full_object=True, filter_id=filter_id)
    dir = DirectoryListing('tvshows')
    for item in group:
        dir.append(item.get_listitem())


@routing_plugin.route('/menu/series/<series_id>')
def show_series_menu(series_id):
    from shoko_models.v2 import Series
    series = Series(series_id, build_full_object=True)

    if len(series.episode_types) > 1:
        dir = DirectoryListing('seasons')
        # type listing
        for item in series.episode_types:
            dir.append(item.get_listitem())
    else:
        dir = DirectoryListing('episodes')
        for item in series:
            dir.append(item.get_listitem())


@routing_plugin.route('/menu/series/<series_id>/type/<episode_type>')
def show_series_episode_types_menu(series_id, episode_type):
    from shoko_models.v2 import SeriesTypeList
    types = SeriesTypeList(series_id, episode_type)
    dir = DirectoryListing('episodes')
    for item in types:
        dir.append(item.get_listitem())


@routing_plugin.route('/dialog/wizard')
def show_wizard_dialog():
    pass


@routing_plugin.route('/dialog/vote_series/<series_id>')
def show_series_vote_dialog(series_id):
    pass


@routing_plugin.route('/dialog/vote_episode/<ep_id>')
def show_episode_vote_dialog(ep_id):
    pass


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play/<is_movie>/<mark_as_watched>')
def play_video(file_id, ep_id=0, is_movie=False, mark_as_watched=True):
    pass


@routing_plugin.route('/series/<series_id>/vote/<value>')
def vote_for_series(series_id, value):
    pass


@routing_plugin.route('/episode/<ep_id>/vote/<value>')
def vote_for_episode(ep_id, value):
    pass


@routing_plugin.route('/episode/<ep_id>/set_watched/<watched>')
def set_episode_watched_status(ep_id, watched):
    pass


@routing_plugin.route('/series/<series_id>/set_watched/<watched>')
def set_series_watched_status(series_id, watched):
    pass


@routing_plugin.route('/group/<group_id>/set_watched/<watched>')
def set_group_watched_status(group_id, watched):
    pass


if __name__ == '__main__':
    debug.debug_init()
    routing_plugin.run()
