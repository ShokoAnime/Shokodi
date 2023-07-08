# -*- coding: utf-8 -*-
"""
here are functions needed to create dirs/files
"""
import json
import sys

import xbmcgui

from lib.nakamori_utils import model_utils, kodi_utils
from lib.nakamori_utils.globalvars import *
from lib.proxy.python_version_proxy import python_proxy as pyproxy

plugin_localize = plugin_addon.getLocalizedString


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
        # busy.create(plugin_localize(30160), plugin_localize(30161))
        # busy.update(20)
        temp_url = params['url']
        temp_url = pyproxy.set_parameter(temp_url, 'level', 2)

        # busy.update(10)
        temp_url = pyproxy.set_parameter(temp_url, 'nocast', 0)
        temp_url = pyproxy.set_parameter(temp_url, 'notag', 0)
        temp_url = pyproxy.set_parameter(temp_url, 'level', 0)
        # busy.update(20)
        html = pyproxy.get_json(temp_url)
        # busy.update(50, plugin_localize(30162))
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
            kodi_utils.set_window_heading('Nakamori', body.get('name', ''))
        except:
            kodi_utils.set_window_heading('Nakamori', plugin_localize(30222))

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
    kodi_utils.set_window_heading('Nakamori', plugin_localize(30115))

    items = [{
        'title': plugin_localize(30122),
        'cmd': 'missing',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_localize(30135),
        'extras': ''
    }, {
        'title': plugin_localize(30117),
        'cmd': 'statsupdate',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_localize(30136),
        'extras': ''
    }, {
        'title': plugin_localize(30118),
        'cmd': 'mediainfo',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_localize(30137),
        'extras': ''
    }, {
        'title': plugin_localize(30116),
        'cmd': 'folderlist',
        'poster': 'none',
        'icon': os.path.join(plugin_img_path, 'icons', 'new-search.png'),
        'fanart': os.path.join(plugin_img_path, 'backgrounds', 'new-search.png'),
        'type': 'video',
        'plot': plugin_localize(30140),
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
