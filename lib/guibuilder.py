# -*- coding: utf-8 -*-
"""
here are functions needed to create dirs/files
"""
import json
import sys

import nakamori_utils.kodi_utils
import nakamori_utils.shoko_utils
import xbmcgui
import search
from nakamori_utils import model_utils, kodi_utils
from nakamori_utils.globalvars import *
from proxy.python_version_proxy import python_proxy as pyproxy


def build_cast_menu(params):
    """
    Build the cast menu for 3.8.2+
    :param params:
    :return:
    """
    try:
        search_url = server + '/api/cast/byseries'
        if params.get('serie_id', '') == '':
            return
        search_url = pyproxy.set_parameter(search_url, 'id', params.get('serie_id', ''))
        search_url = pyproxy.set_parameter(search_url, 'notag', 1)
        search_url = pyproxy.set_parameter(search_url, 'level', 0)
        cast_nodes = json.loads(pyproxy.get_json(search_url))

        base_search_url = server + '/api/cast/search'
        base_search_url = pyproxy.set_parameter(base_search_url, 'fuzzy', 0)

        if len(cast_nodes) > 0:
            if cast_nodes[0].get('character', '') == '':
                return

            # xbmcplugin.setContent(handle, 'tvshows')
            for cast in cast_nodes:
                character = cast.get(u'character', u'')
                character_image = server + cast.get('character_image', '')
                character_description = cast.get('character_description')
                staff = cast.get('staff', '')
                staff_image = server + cast.get('staff_image', '')

                liz = xbmcgui.ListItem(staff)
                new_search_url = pyproxy.set_parameter(base_search_url, 'query', staff)

                details = {
                    'mediatype': 'episode',
                    'title': staff,
                    'originaltitle': staff,
                    'sorttitle': staff,
                    'genre': character,

                }

                if character_description is not None:
                    character_description = model_utils.remove_anidb_links(character_description)
                    details['plot'] = character_description

                liz.setInfo(type='video', infoLabels=details)

                if staff_image != '':
                    liz.setArt({'thumb': staff_image,
                                'icon': staff_image,
                                'poster': staff_image})
                if character_image != '':
                    liz.setArt({'fanart': character_image})

                u = sys.argv[0]
                u = pyproxy.set_parameter(u, 'mode', 1)
                u = pyproxy.set_parameter(u, 'name', params.get('name', 'Cast'))
                u = pyproxy.set_parameter(u, 'url', new_search_url)
                u = pyproxy.set_parameter(u, 'cmd', 'searchCast')

                # list_items.append((u, liz, True))

            # end_of_directory(place='filter')
    except:
        pass


def build_search_directory():
    """
    Build Search directory 'New Search' and read Search History
    :return:
    """
    items = [{
        'title': plugin_addon.getLocalizedString(30224),
        'url': server + '/api/serie',
        'mode': 3,
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': '',
        'plot': '',
        'extras': 'true-search'
    }, {
        'title': '[COLOR yellow]Clear Search Terms[/COLOR]',
        'url': 'delete-all',
        'mode': 31,
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'clear-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'clear-search.png'),
        'type': '',
        'plot': '',
        'extras': ''
    }]

    # read search history
    search_history = search.get_search_history()
    search_history.sort()
    for ss in search_history:
        try:
            if len(ss[0]) > 0:
                items.append({
                    'title': ss[0],
                    'url': server + '/api/search',
                    'query': ss[0],
                    'mode': 3,
                    'poster': 'none',
                    'icon': os.path.join(plugin_img_path, 'icons', 'search.png'),
                    'fanart': os.path.join(plugin_img_path, 'backgrounds', 'search.png'),
                    'type': '',
                    'plot': '',
                    'extras': 'force-search',
                    'extras2': 'db-search'
                })
        except:
            pass

    for detail in items:
        u = sys.argv[0]
        u = pyproxy.set_parameter(u, 'url', detail['url'])
        u = pyproxy.set_parameter(u, 'mode', detail['mode'])
        u = pyproxy.set_parameter(u, 'name', pyproxy.encode(detail['title']))
        u = pyproxy.set_parameter(u, 'extras', detail['extras'])
        if 'query' in detail:
            u = pyproxy.set_parameter(u, 'query', detail['query'])
        liz = xbmcgui.ListItem(pyproxy.encode(detail['title']))
        liz.setArt({'thumb': detail['icon'],
                    'poster': detail['poster'],
                    'icon': detail['icon'],
                    'fanart': detail['fanart']})
        liz.setInfo(type=detail['type'], infoLabels={'Title': pyproxy.encode(detail['title']), 'Plot': detail['plot']})
        #list_items.append((u, liz, True))
    #end_of_directory(False)


def build_serie_soon(params):
    """
        Builds the list of items for Calendar via Directory and ListItems ( Basic Mode )
        Args:
            params:
        Returns:

        """
    # xbmcplugin.setContent(handle, 'tvshows')
    # xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)

    try:
        # busy.create(plugin_addon.getLocalizedString(30160), plugin_addon.getLocalizedString(30161))
        # busy.update(20)
        temp_url = params['url']
        temp_url = pyproxy.set_parameter(temp_url, 'level', 2)

        # busy.update(10)
        temp_url = pyproxy.set_parameter(temp_url, 'nocast', 0)
        temp_url = pyproxy.set_parameter(temp_url, 'notag', 0)
        temp_url = pyproxy.set_parameter(temp_url, 'level', 0)
        # busy.update(20)
        html = pyproxy.get_json(temp_url)
        # busy.update(50, plugin_addon.getLocalizedString(30162))
        if plugin_addon.getSetting('spamLog') == 'true':
            xbmc.log(params['url'], xbmc.LOGWARNING)
            xbmc.log(html, xbmc.LOGWARNING)
        # busy.update(70)
        temp_url = params['url']
        temp_url = pyproxy.set_parameter(temp_url, 'level', 2)
        html = pyproxy.get_json(temp_url)
        body = json.loads(html)
        # busy.update(100)
        # busy.close()

        # check if this is maybe filter-inception
        try:
            kodi_utils.set_window_heading(body.get('name', ''))
        except:
            kodi_utils.set_window_heading(plugin_addon.getLocalizedString(30222))

        try:
            parent_title = body.get('name', '')
            used_dates = []
            for sers in body['series']:
                # region add_date
                if sers.get('air', '') not in used_dates:
                    used_dates.append(sers.get('air', ''))
                    soon_url = server + '/api/serie/soon'
                    details = {'aired': sers.get('air', ''), 'title': sers.get('air', '')}
                    u = sys.argv[0]
                    u = pyproxy.set_parameter(u, 'url', soon_url)
                    u = pyproxy.set_parameter(u, 'mode', str(0))
                    u = pyproxy.set_parameter(u, 'name', details.get('title', ''))
                    extra_data = {'type': 'pictures'}
                    # add_gui_item(u, details, extra_data)
                # endregion

                # add_serie_item(sers, parent_title)

        except Exception as e:
            # nt.error('util.error during build_serie_soon date_air', str(e))
            pass
    except Exception as e:
        # nt.error('Invalid JSON Received in build_serie_soon', str(e))
        pass
    # end_of_directory()


def search_for(search_url):
    """
    Actually do the search and build the result
    :param search_url: search url with query
    """
    try:
        search_url = pyproxy.set_parameter(search_url, 'tags', 2)
        search_url = pyproxy.set_parameter(search_url, 'level', 1)
        search_url = pyproxy.set_parameter(search_url, 'limit', plugin_addon.getSetting('maxlimit'))
        search_url = pyproxy.set_parameter(search_url, 'limit_tag', plugin_addon.getSetting('maxlimit_tag'))
        json_body = json.loads(pyproxy.get_json(search_url))
        if json_body['groups'][0]['size'] == 0:
            xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % (plugin_addon.getLocalizedString(30180),
                                                                            plugin_addon.getLocalizedString(30181),
                                                                            '!', plugin_addon.getAddonInfo('icon')))
        else:
            search_url = pyproxy.parse_parameters(search_url)
            # build_groups_menu(search_url, json_body)
    except:
        pass


def execute_search_and_add_query():
    """
    Build a search query and if its not in Search History add it
    """
    find = nakamori_utils.kodi_utils.search_box()
    # check search history
    if find == '':
        build_search_directory()
        return
    if not search.check_in_database(find):
        # if its not add to history & refresh
        search.add_search_history(find)
        xbmc.executebuiltin('Container.Refresh')
    search_url = server + '/api/search'
    search_url = pyproxy.set_parameter(search_url, 'query', find)
    search_for(search_url)


def create_playlist(serie_id):
    """
    Create playlist of all episodes that wasn't watched
    :param serie_id:
    :return:
    """
    serie_url = server + '/api/serie?id=' + str(serie_id) + '&level=2&nocast=1&notag=1'
    serie_body = json.loads(pyproxy.get_json(serie_url))
    # playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    # playlist.clear()
    item_count = 0
    ep_list = []
    # TODO sort by epnumber and eptype so it wont get mixed
    if 'eps' in serie_body and len(serie_body['eps']) > 0:
        for serie in serie_body['eps']:
            if len(serie['files']) > 0:
                if 'view' in serie and serie['view'] == 1:
                    continue
                ep_id = serie['id']
                # video = serie['files'][0]['url']
                # details = add_serie_item(serie, serie_body['name'], True)
                # liz = xbmcgui.ListItem(details.get('title', 'Unknown'))
                # liz.setInfo(type='Video', infoLabels=details)
                item_count += 1
                # playlist.add(url=video, listitem=liz, index=item_count)
                ep_list.append(ep_id)
    if len(ep_list) > 0:
        # xbmc.Player().play(playlist)
        for ep in ep_list:
            xbmc.log('play this : ' + str(ep), xbmc.LOGWARNING)
            video_parameters = dict()
            video_parameters['ep_id'] = str(ep)
            # play it


def build_shoko_menu():
    """
    build menu with items to interact with shoko server via api
    :return:
    """
    # xbmcplugin.setContent(handle, 'tvshows')
    kodi_utils.set_window_heading(plugin_addon.getLocalizedString(30115))

    items = [{
        'title': plugin_addon.getLocalizedString(30122),
        'cmd': 'missing',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_addon.getLocalizedString(30135),
        'extras': ''
    }, {
        'title': plugin_addon.getLocalizedString(30117),
        'cmd': 'statsupdate',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_addon.getLocalizedString(30136),
        'extras': ''
    }, {
        'title': plugin_addon.getLocalizedString(30118),
        'cmd': 'mediainfo',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_addon.getLocalizedString(30137),
        'extras': ''
    }, {
        'title': plugin_addon.getLocalizedString(30116),
        'cmd': 'folderlist',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_addon.getLocalizedString(30140),
        'extras': '',
    }]

    for detail in items:
        u = sys.argv[0]
        if 'cmd' in detail:
            u = pyproxy.set_parameter(u, 'cmd', detail['cmd'])
        if 'vl' in detail:
            u = pyproxy.set_parameter(u, 'vl', detail['vl'])
        u = pyproxy.set_parameter(u, 'name', pyproxy.encode(detail['title']))
        u = pyproxy.set_parameter(u, 'extras', detail['extras'])
        liz = xbmcgui.ListItem(pyproxy.encode(detail['title']))
        liz.setArt({'thumb': detail['icon'],
                    'poster': detail['poster'],
                    'icon': detail['icon'],
                    'fanart': detail['fanart']})
        liz.setInfo(type=detail['type'], infoLabels={'Title': pyproxy.encode(detail['title']), 'Plot': detail['plot']})
        # list_items.append((u, liz, True))
    # end_of_directory(False)
