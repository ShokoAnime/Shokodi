# THIS IS A SUPPLEMENTARY FILE UNTIL WE GET THE ROUTING REGISTRY
# Yes this was super tedious and the reason that I want a routing registry
import xbmc
from lib.proxy.python_version_proxy import python_proxy as pyproxy

run = 'RunScript(plugin.video.nakamori,%s)'


def url_series_info(id=0, aid=0):
    if aid > 0:
        url = '/seriesinfo/aid/%s/' % aid
    else:
        url = '/seriesinfo/%s/' % id
    return run % url


def series_info(id=0, aid=0):
    url = url_series_info(id, aid)
    xbmc.executebuiltin(url)


def arbiter(wait, arg):
    url = '/arbiter/%i/%s' % (wait, arg)
    url = run % url
    xbmc.executebuiltin(url)


def url_wizard_connection():
    url = '/dialog/wizard/connection'
    return run % url


def wizard_connection():
    url = url_wizard_connection()
    xbmc.executebuiltin(url, True)


def url_wizard_login():
    url = '/dialog/wizard/login'
    return run % url


def wizard_login():
    url = url_wizard_login()
    xbmc.executebuiltin(url, True)


def url_whats_new():
    url = '/dialog/whats_new'
    return run % url


def whats_new():
    url = url_whats_new()
    xbmc.executebuiltin(url)


def url_settings():
    url = '/dialog/settings'
    return run % url


def url_script_settings():
    url = '/dialog/script_settings'
    return run % url


def settings():
    url = url_settings()
    xbmc.executebuiltin(url)


def url_shoko_menu():
    url = '/dialog/shoko'
    return run % url


def shoko_menu():
    url = url_shoko_menu()
    xbmc.executebuiltin(url)


def url_new_search(save):
    url = '/dialog/search/%s' % save
    return run % url


def new_search(save):
    url = url_new_search(save)
    xbmc.executebuiltin(url, True)


def url_remove_search_term(query):
    url = '/search/remove/%s' % pyproxy.quote(pyproxy.quote(query))
    return run % url


def remove_search_term(query):
    url = url_remove_search_term(query)
    xbmc.executebuiltin(url, True)


def url_clear_search_terms():
    url = '/search/clear'
    return run % url


def clear_search_terms():
    url = url_clear_search_terms()
    xbmc.executebuiltin(url, True)


def url_clear_listitem_cache():
    url = '/kodi/clear_listitem_cache'
    return run % url


def clear_listitem_cache():
    url = url_clear_listitem_cache()
    xbmc.executebuiltin(url, True)


def url_clear_image_cache():
    url = '/kodi/clear_image_cache'
    return run % url


def clear_image_cache():
    url = url_clear_image_cache()
    xbmc.executebuiltin(url, True)


def url_refresh():
    url = '/refresh'
    return run % url


def refresh():
    url = url_refresh()
    xbmc.executebuiltin(url, True)


def url_show_series_vote_dialog(series_id):
    url = '/dialog/vote_series/%i/' % series_id
    return run % url


def show_series_vote_dialog(series_id):
    url = url_show_series_vote_dialog(series_id)
    xbmc.executebuiltin(url)


def url_show_episode_vote_dialog(ep_id):
    url = '/dialog/vote_episode/%i/' % ep_id
    return run % url


def show_episode_vote_dialog(ep_id):
    url = url_show_episode_vote_dialog(ep_id)
    xbmc.executebuiltin(url)


def url_vote_for_series(series_id):
    url = '/series/%i/vote' % series_id
    return run % url


def vote_for_series(series_id, wait=False):
    url = url_vote_for_series(series_id)
    xbmc.executebuiltin(url, wait)


def url_vote_for_episode(ep_id):
    url = '/episode/%i/vote' % ep_id
    return run % url


def vote_for_episode(ep_id, wait=False):
    url = url_vote_for_episode(ep_id)
    xbmc.executebuiltin(url, wait)


def url_file_list(ep_id):
    url = '/ep/%i/file_list' % ep_id
    return run % url


def file_list(ep_id):
    url = url_file_list(ep_id)
    xbmc.executebuiltin(url, True)


def url_rescan_file(file_id):
    url = '/file/%i/rescan' % file_id
    return run % url


def rescan_file(file_id):
    url = url_rescan_file(file_id)
    xbmc.executebuiltin(url)


def url_rehash_file(file_id):
    url = '/file/%i/rehash' % file_id
    return run % url


def rehash_file(file_id):
    url = url_rehash_file(file_id)
    xbmc.executebuiltin(url)


def url_episode_watched_status(ep_id, watched):
    url = '/episode/%i/set_watched/%s' % (ep_id, watched)
    return run % url


def set_episode_watched_status(ep_id, watched, wait=False):
    url = url_episode_watched_status(ep_id, watched)
    xbmc.executebuiltin(url, wait)


def url_series_watched_status(series_id, watched):
    url = '/series/%i/set_watched/%s' % (series_id, watched)
    return run % url


def set_series_watched_status(series_id, watched, wait=False):
    url = url_series_watched_status(series_id, watched)
    xbmc.executebuiltin(url, wait)


def url_group_watched_status(group_id, watched):
    url = '/group/%i/set_watched/%s' % (group_id, watched)
    return run % url


def set_group_watched_status(group_id, watched, wait=False):
    url = url_group_watched_status(group_id, watched)
    xbmc.executebuiltin(url, wait)


def url_move_to_item(index):
    url = '/menu/episode/move_to_item/%i/' % index
    return run % url


def move_to_item(index):
    url = url_move_to_item(index)
    xbmc.executebuiltin(url)


def url_probe_file(file_id):
    url = '/file/%i/probe' % file_id
    return run % url


def url_probe_episode(ep_id):
    url = '/episode/%i/probe' % ep_id
    return run % url


def url_transcode_file(file_id):
    url = '/file/%i/transcode' % file_id
    return run % url


def url_transcode_episode(ep_id):
    url = '/episode/%i/transcode' % ep_id
    return run % url
