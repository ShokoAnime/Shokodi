# -*- coding: utf-8 -*-
import re
from collections import defaultdict

from lib import error_handler as eh
from lib.error_handler import ErrorPriority
from lib.utils.globalvars import *
from lib.proxy.kodi import kodi_proxy as kproxy, kodi_proxy
from lib.proxy.python import proxy as pyproxy


def get_tags(tag_node):
    """
    Get the tags from the new style
    Args:
        tag_node: node containing group

    Returns: a string of all of the tags formatted

    """
    try:
        if tag_node is None:
            return ''
        if len(tag_node) == 0:
            return ''
        short_tag = plugin_addon.getSetting('short_tag_list') == 'true'
        temp_genres = []
        current_length = 0
        # the '3' here is because the separator ' | ' is 3 chars
        for tag in tag_node:
            if pyproxy.is_string(tag):
                if short_tag and current_length + len(tag) + 3 > 50:
                    break
                temp_genres.append(tag)
                current_length += len(tag) + 3
            else:
                temp_genre = pyproxy.decode(tag['tag']).strip()
                if short_tag and current_length + len(temp_genre) + 3 > 50:
                    break
                temp_genres.append(temp_genre)
                current_length += len(temp_genre) + 3
        return kproxy.parse_tags(temp_genres)
    except:
        eh.exception(ErrorPriority.NORMAL)
        return ''


def get_cast_and_role_new(data, fix_seiyuu_pic=False):
    """
    Get cast from the json and arrange in the new setCast format
    :param data: json node containing 'roles'
    :param fix_seiyuu_pic: bool for swapping character picture with seiyuu's
    :type data: list
    :return: a list of dictionaries for the cast
    :rtype: List[Dict[str,str]]
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char.get('character', '')
            char_seiyuuname = char.get('staff', '')
            if fix_seiyuu_pic:
                char_seiyuupic = server + char.get('staff_image', '')
            else:
                char_seiyuupic = server + char.get('character_image', '')

            # only add it if it has data
            # reorder these to match the convention (Actor is cast, character is role, in that order)
            if len(char_charname) != 0:
                actor = {
                    'name':         char_seiyuuname,
                    'role':         char_charname,
                    'thumbnail':    char_seiyuupic
                }
                result_list.append(actor)
        if len(result_list) == 0:
            return None
        return result_list
    return None


def get_cast_and_role(data, fix_seiyuu_pic=False):
    """
    Get cast from the json and arrange in the new setCast format
    Args:
        data: json node containing 'roles'
        fix_seiyuu_pic: bool for swapping character picture with seiyuu's
    Returns: a list of dictionaries for the cast
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char['role']
            char_seiyuuname = char['name']
            if fix_seiyuu_pic:
                char_seiyuupic = char['seiyuupic']
            else:
                char_seiyuupic = char['rolepic']

            # only add it if it has data
            # reorder these to match the convention (Actor is cast, character is role, in that order)
            if len(char_charname) != 0:
                actor = {
                    'name':         char_seiyuuname,
                    'role':         char_charname,
                    'thumbnail':    char_seiyuupic
                }
                result_list.append(actor)
        if len(result_list) == 0:
            return None
        return result_list
    return None


def convert_cast_and_role_to_legacy(list_of_dicts):
    """
    Convert standard cast_and_role to version supported by Kodi16 and lower
    :param list_of_dicts:
    :return: list
    """

    list_cast = []
    list_cast_and_role = []
    if list_of_dicts is not None and len(list_of_dicts) > 0:
        for actor in list_of_dicts:
            seiyuu = actor.get('name', '')
            role = actor.get('role', '')
            if len(role) != 0:
                list_cast.append(role)
                if len(seiyuu) != 0:
                    list_cast_and_role.append((seiyuu, role))
    return list_cast, list_cast_and_role


def is_type_list(title):
    """
    Returns if a title matches an episode type
    :param title:
    :return:
    """
    if title == 'ova' or title == 'ovas':
        return True
    if title == 'episode' or title == 'episodes':
        return True
    if title == 'special' or title == 'specials':
        return True
    if title == 'parody' or title == 'parodies':
        return True
    if title == 'credit' or title == 'credits':
        return True
    if title == 'trailer' or title == 'trailers':
        return True
    if title == 'other' or title == 'others':
        return True
    return False


def get_title(data, lang=None, title_type=None):
    """
    Get the title based on settings
    :param data: json node containing the title
    :return: string of the desired title
    :rtype: str

    """
    try:
        if 'titles' not in data or plugin_addon.getSetting('use_server_title') == 'true':
            return pyproxy.decode(data.get('name', ''))
        # xbmc.log(data.get('title', 'Unknown'))
        title = pyproxy.decode(data.get('name', '').lower())
        if is_type_list(title):
            return pyproxy.decode(data.get('name', ''))

        if lang is None:
            lang = plugin_addon.getSetting('displaylang')
        if title_type is None:
            title_type = plugin_addon.getSetting('title_type')

        # try to match
        title = match_title(data, lang, title_type)
        if title is not None:
            return title

        # fallback on any type of same language
        title = match_title(data, lang, '!short')
        if title is not None:
            return title

        # fallback on x-jat main title
        title = match_title(data, 'x-jat', 'main')
        if title is not None:
            return title

        # fallback on directory title
        return pyproxy.decode(data.get('name', ''))
    except:
        eh.exception(ErrorPriority.NORMAL)
        return 'util.error'


def match_title(data, lang, title_type):
    try:
        exclude = False
        if title_type.startswith('!'):
            title_type = title_type[1:]
            exclude = True

        for title_tag in data.get('titles', []):
            title = pyproxy.decode(title_tag.get('Title', ''))
            if pyproxy.decode(title_tag.get('Title', '')) == '':
                continue

            if title_tag.get('Language', '').lower() != lang.lower():
                continue
            # does it match the proper type
            if exclude and title_tag.get('Type', '').lower() == title_type.lower():
                continue

            if not exclude and title_tag.get('Type', '').lower() != title_type.lower():
                continue

            return title
        return None
    except:
        eh.exception(ErrorPriority.NORMAL)
        return None


def video_file_information(node, detail_dict):
    """
    Process given 'node' and parse it to create proper file information dictionary 'detail_dict'
    :param node: node that contains file
    :param detail_dict: dictionary for output
    :return: dict
    """
    detail_dict['VideoStreams'] = get_video_streams(node)
    detail_dict['AudioStreams'] = get_audio_streams(node)
    detail_dict['SubStreams'] = get_sub_streams(node)


def get_video_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if 'videos' in node:
        for stream_node in node['videos']:
            stream_info = node['videos'][stream_node]
            if not isinstance(stream_info, dict):
                continue
            stream_id = int(stream_info.get('Index', '0'))
            streams[stream_id]['codec'] = stream_info['Codec']
            streams[stream_id]['width'] = stream_info['Width']
            streams[stream_id]['height'] = stream_info['Height']
            if 'width' not in streams or 'height' not in streams:
                streams['width'] = stream_info['Width']
                streams['height'] = stream_info['Height']
            streams[stream_id]['aspect'] = round(float(streams['width']) / float(streams['height']), 2)
    return streams


def get_audio_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if 'audios' in node:
        for stream_node in node['audios']:
            stream_info = node['audios'][stream_node]
            if not isinstance(stream_info, dict):
                continue
            stream_id = int(stream_info.get('Index', '0'))
            # there are some codecs like AC3 that are really called AC3+, but Kodi doesn't do the +
            streams[stream_id]['codec'] = stream_info['Codec'].replace('+', '')
            streams[stream_id]['language'] = stream_info['LanguageCode'] if 'LanguageCode' in stream_info else 'unk'
            streams[stream_id]['channels'] = int(stream_info['Channels']) if 'Channels' in stream_info else 2
    return streams


def get_sub_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if 'subtitles' in node:
        i = 0
        for stream_node in node['subtitles']:
            stream_info = node['subtitles'][stream_node]
            if not isinstance(stream_info, dict):
                continue
            try:
                stream_id = int(stream_node)
            except:
                stream_id = i
            streams[stream_id]['language'] = stream_info['LanguageCode'] if 'LanguageCode' in stream_info else 'unk'
            i += 1
    return streams


def get_cast_info(json_node, fix_seiyuu_pic=False):
    """
    Extracts and processes cast and staff info
    :param json_node: json response
    :param fix_seiyuu_pic: bool for swapping character picture with seiyuu's
    :return: list of cast objects { 'name': str, 'role': str, 'thumbnail': str (url) }
    :rtype:
    """
    result_list = []
    if 'roles' in json_node:
        cast_nodes = json_node.get('roles', {})
        if len(cast_nodes) > 0:
            if cast_nodes[0].get('character', '') != '':
                result_list = get_cast_and_role_new(cast_nodes, fix_seiyuu_pic)
            else:
                result_list = get_cast_and_role(cast_nodes, fix_seiyuu_pic)
    return result_list


def get_airdate(json_node):
    """
    get the air from json, removing default value
    :param json_node: the json response
    :return: str date or ''
    :rtype: str
    """
    air = json_node.get('air', '')
    if air == '0001-01-01' or air == '01-01-0001':
        air = ''
    return air


def get_date(date):
    """
    get date format from air date
    :param date: 'air'
    :type date: str
    :return:
    """
    temp_date = date.split('-')
    if len(temp_date) == 3:  # format is 2016-01-24, we want it 24.01.2016
        return temp_date[1] + '.' + temp_date[2] + '.' + temp_date[0]
    return None


def get_sort_name(episode):
    """
    gets the sort name from an episode
    :param episode:
    :type episode: Episode
    :return:
    """
    return str(episode.episode_number).zfill(3) + ' ' + episode.name


def get_first(iterable):
    if isinstance(iterable, list) and len(iterable) > 0:
        return next((i for i in iterable if isinstance(i, (list, dict, defaultdict))))
    if isinstance(iterable, (dict, defaultdict)) and len(iterable) > 0:
        return next((v for k, v in iterable.items() if isinstance(v, (list, dict, defaultdict))))
    return iterable


# noinspection Duplicates
def set_stream_info(listitem, f):
    """
    :param listitem: the ListItem to set data
    :type listitem: ListItem
    :param f: the file object to pull data from
    :type f: File
    """
    video = f.video_streams
    if video is not None and len(video) > 0:
        video = get_first(video)
        listitem.add_stream_info('video', video)

        listitem.set_property('VideoResolution', str(video.get('height', '')))
        listitem.set_property('VideoCodec', video.get('codec', ''))
        listitem.set_property('VideoAspect', str(video.get('aspect', '')))

    audio = f.audio_streams
    if audio is not None and len(audio) > 0:
        first = get_first(audio)
        listitem.set_property('AudioCodec', first.get('codec', ''))
        listitem.set_property('AudioChannels', str(first.get('channels', '')))
        for stream in audio:
            if not isinstance(audio[stream], dict):
                continue
            listitem.set_property('AudioCodec.' + str(stream), str(audio[stream]['codec']))
            listitem.set_property('AudioChannels.' + str(stream), str(audio[stream]['channels']))
            listitem.add_stream_info('audio', audio[stream])

    subs = f.sub_streams
    if subs is not None and len(subs) > 0:
        for stream2 in subs:
            listitem.set_property('SubtitleLanguage.' + str(stream2), str(subs[stream2]['language']))
            listitem.add_stream_info('subtitle', subs[stream2])


def make_text_nice(data=''):
    """
    Make any anidb text look nice, clean and sleek by removing links, annotations, comments, empty lines
    :param data: text that is too ugly to be shown
    :return: text that is a bit nicer
    """
    data = remove_anidb_links(data)
    # the only one I could care to make settings if someone ask for
    data = remove_anidb_annotations(data)
    data = remove_anidb_comments(data)
    data = remove_multi_empty_lines(data)
    return data


def remove_anidb_links(data=''):
    """
    Remove anidb links from descriptions
    Args:
        data: the strong to remove links from

    Returns: new string without links

    """
    p = re.compile(r'(https?://anidb\.net/[0-9A-z/\-_.?=&]+ *\[)([\S ]+?)(])')
    return p.sub(r'\2', data)


def remove_anidb_comments(data=''):
    """
    Remove comments that topically start with *, --, ~ from description
    :param data: text to clean
    :return: text after clean
    """
    data = re.sub(r'^(\*|--|~) .*', "", data, flags=re.MULTILINE)
    return data.strip(" \n")


def remove_anidb_annotations(data=''):
    """
    Remove annotations containing Source, Note, Summary from description
    :param data: text to clean
    :return: text after clean
    """
    data = re.sub(r'\n(Source|Note|Summary):.*', "", data, flags=re.DOTALL)
    return data.strip(" \n")


def remove_multi_empty_lines(data=''):
    """
    Remove multiply empty lines to save some space
    :param data: text to clean
    :return: text after clean
    """
    data = re.sub(r'\n\n+', r'\n\n', data)
    return data.strip(" \n")


def add_default_parameters(url, obj_id, level):
    key = pyproxy.set_parameter(url, 'id', obj_id)
    key = pyproxy.set_parameter(key, 'level', level)
    key = pyproxy.set_parameter(key, 'tagfilter', tag_setting_flags)
    if plugin_addon.getSetting('request_nocast') == 'true':
        key = pyproxy.set_parameter(key, 'nocast', 1)
    return key


def show_file_list(files):
    """
    Create DialogBox with file list to pick if there is more than 1 file for episode
    :param files: list of tuples of names to the object
    :type files: List[Tuple[str,int]]
    :return: int (id of picked file or 0 if none)
    """
    if len(files) > 1:
        items = [x[0] for x in files]
        my_file = kodi_proxy.Dialog.select(plugin_addon.getLocalizedString(30196), items)
        if my_file > -1:
            return files[my_file][1]
        else:
            # cancel -1,0
            return 0
    elif len(files) == 1:
        return files[0][1]
    else:
        return 0
