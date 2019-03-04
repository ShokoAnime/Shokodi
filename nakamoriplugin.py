import json
import sys

import routing
from lib import kodi_utils
from nakamori_utils.globalvars import *
from kodi_models.kodi_models import DirectoryListing
import debug
from nakamori_utils import nakamoritools as nt

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
    filter = Filter(filter_id, build_full_object=True, get_children=True)
    dir = DirectoryListing('tvshows')
    items = []
    for item in filter:
        items.append(item)
    # sort the filters
    try:
        # if they are all zero, preserve server sorting
        if any(x.sort_index != 0 for x in items):
            items.sort(key=lambda a: (a.sort_index, a.name))
    except:
        pass
    for item in items:
        dir.append(item.get_listitem())
    del dir


# apparently the issues are related to not having any arguments. It works fine if you give it a bool that means nothing
@routing_plugin.route('/menu/filter/unsorted/<nothing>')
def show_unsorted_menu(nothing):
    # this is really bad practice, but the unsorted files list is too special
    from shoko_models.v2 import File
    url = server + '/api/file/unsort'
    json_body = nt.get_json(url, True)
    json_node = json.loads(json_body)

    dir = DirectoryListing('episodes')
    for item in json_node:
        f = File(item)
        dir.append(f.get_listitem())


@routing_plugin.route('/menu/group/<group_id>/filterby/<filter_id>')
def show_group_menu(group_id, filter_id):
    from shoko_models.v2 import Group
    group = Group(group_id, build_full_object=True, get_children=True, filter_id=filter_id)
    dir = DirectoryListing('tvshows')
    for item in group:
        dir.append(item.get_listitem())


@routing_plugin.route('/menu/series/<series_id>')
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
            if item.get_file() is None:
                continue
            dir.append(item.get_listitem(), False)


@routing_plugin.route('/menu/series/<series_id>/type/<episode_type>')
def show_series_episode_types_menu(series_id, episode_type):
    from shoko_models.v2 import SeriesTypeList
    types = SeriesTypeList(series_id, episode_type)
    dir = DirectoryListing('episodes')
    for item in types:
        if item.get_file() is None:
            continue
        dir.append(item.get_listitem(), False)


@routing_plugin.route('/dialog/wizard')
def show_wizard_dialog():
    pass


@routing_plugin.route('/dialog/vote_series/<series_id>')
def show_series_vote_dialog(series_id):
    pass


@routing_plugin.route('/dialog/vote_episode/<ep_id>')
def show_episode_vote_dialog(ep_id):
    pass


def play_video_internal(ep_id, file_id, mark_as_watched=True, resume=False):
    # all of real work is done here
    kodi_utils.play_video(file_id, ep_id, mark_as_watched, resume)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play')
def play_video(ep_id, file_id):
    play_video_internal(ep_id, file_id)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/play_without_marking')
def play_video_without_marking(ep_id, file_id):
    play_video_internal(ep_id, file_id, mark_as_watched=False)


@routing_plugin.route('/episode/<ep_id>/file/<file_id>/resume')
def resume_video(ep_id, file_id):
    # if we are resuming, then we'll assume that scrobbling and marking are True
    play_video_internal(ep_id, file_id, mark_as_watched=True, resume=True)


@routing_plugin.route('/series/<series_id>/vote/<value>')
def vote_for_series(series_id, value):
    pass


@routing_plugin.route('/episode/<ep_id>/vote/<value>')
def vote_for_episode(ep_id, value):
    pass


@routing_plugin.route('/episode/<ep_id>/set_watched/<watched>')
def set_episode_watched_status(ep_id, watched):
    from shoko_models.v2 import Episode
    ep = Episode(ep_id)
    ep.set_watched_status(watched)


@routing_plugin.route('/series/<series_id>/set_watched/<watched>')
def set_series_watched_status(series_id, watched):
    from shoko_models.v2 import Series
    series = Series(series_id)
    series.set_watched_status(watched)


@routing_plugin.route('/group/<group_id>/set_watched/<watched>')
def set_group_watched_status(group_id, watched):
    from shoko_models.v2 import Group
    group = Group(group_id)
    group.set_watched_status(watched)


if __name__ == '__main__':
    debug.debug_init()
    auth, apikey = nt.valid_user()
    if not auth:
        # error
        sys.exit()
    routing_plugin.run()
