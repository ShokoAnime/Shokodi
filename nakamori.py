#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import resources.lib.util as util
import resources.lib.search as search
from resources.lib.calendar import Calendar, Wizard

from collections import defaultdict

import xbmcplugin
import xbmcaddon
import xbmcgui
import xbmc

import sys
import os
import pstats
import cProfile

import datetime

has_pydev = False
has_line_profiler = False
try:
    # noinspection PyUnresolvedReferences
    import line_profiler
    has_line_profiler = True
except ImportError:
    pass

try:
    # noinspection PyUnresolvedReferences
    import pydevd
    has_pydev = True
except ImportError:
    pass

handle = int(sys.argv[1])
listitems = []
busy = xbmcgui.DialogProgress()


def profile_this(func):
    """
    This can be used to profile any function.
    Usage:
    @profile_this
    def function_to_profile(arg, arg2):
        pass
    """

    def profiled_func(*args, **kwargs):
        """
        a small wrapper
        """
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            stream = util.StringIO()
            sortby = 'time'
            ps = pstats.Stats(profile, stream=stream).sort_stats(sortby)
            ps.print_stats()
            xbmc.log('Profiled Function: ' + func.__name__ + '\n' + stream.getvalue(), xbmc.LOGWARNING)
    return profiled_func


def end_of_directory(cache=True):
    """
    Leave this in nakamori.py! It needs to be here to access listitems properly
    Adds all items to the list in batch, and then finalizes it
    """
    xbmcplugin.addDirectoryItems(handle, listitems, len(listitems))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=cache)


def video_file_information(node, detail_dict):
    """
    Process given 'node' and parse it to create proper file information dictionary 'detail_dict'
    :param node: node that contains file
    :param detail_dict: dictionary for output
    :return: dict
    """
    # Video
    if 'VideoStreams' not in detail_dict:
        detail_dict['VideoStreams'] = defaultdict(dict)
    if 'AudioStream' not in detail_dict:
        detail_dict['AudioStreams'] = defaultdict(dict)
    if 'SubStream' not in detail_dict:
        detail_dict['SubStreams'] = defaultdict(dict)

    if "videos" in node:
        for stream_node in node["videos"]:
            stream_info = node["videos"][stream_node]
            if not isinstance(stream_info, dict): 
                continue
            streams = detail_dict.get('VideoStreams', defaultdict(dict))
            stream_id = int(stream_info["Index"])
            streams[stream_id]['VideoCodec'] = stream_info['Codec']
            streams['xVideoCodec'] = stream_info['Codec']
            streams[stream_id]['width'] = stream_info['Width']
            if 'width' not in streams:
                streams['width'] = stream_info['Width']
            streams['xVideoResolution'] = str(stream_info['Width'])
            streams[stream_id]['height'] = stream_info['Height']
            if 'height' not in streams:
                streams['height'] = stream_info['Height']
                streams[stream_id]['aspect'] = round(int(streams['width']) / int(streams['height']), 2)
            streams['xVideoResolution'] += "x" + str(stream_info['Height'])
            streams[stream_id]['duration'] = int(round(float(stream_info.get('Duration', 0)) / 1000, 0))
            detail_dict['VideoStreams'] = streams

    # Audio
    if "audios" in node:
        for stream_node in node["audios"]:
            stream_info = node["audios"][stream_node]
            if not isinstance(stream_info, dict):
                continue
            streams = detail_dict.get('AudioStreams', defaultdict(dict))
            stream_id = int(stream_info["Index"])
            streams[stream_id]['AudioCodec'] = stream_info["Codec"]
            streams['xAudioCodec'] = streams[stream_id]['AudioCodec']
            streams[stream_id]['AudioLanguage'] = stream_info["LanguageCode"] if "LanguageCode" in stream_info \
                else "unk"
            streams[stream_id]['AudioChannels'] = int(stream_info["Channels"]) if "Channels" in stream_info else 1
            streams['xAudioChannels'] = util.safeInt(streams[stream_id]['AudioChannels'])
            detail_dict['AudioStreams'] = streams

    # Subtitle
    if "subtitles" in node:
        i = 0
        for stream_node in node["subtitles"]:
            stream_info = node["subtitles"][stream_node]
            if not isinstance(stream_info, dict):
                continue
            streams = detail_dict.get('SubStreams', defaultdict(dict))
            try:
                stream_id = int(stream_node)
            except:
                stream_id = i
            streams[stream_id]['SubtitleLanguage'] = stream_info["LanguageCode"] if "LanguageCode" in stream_info \
                else "unk"
            detail_dict['SubStreams'] = streams
            i += 1


def add_gui_item(gui_url, details, extra_data, context=None, folder=True, index=0, force_select=False):
    """Adds an item to the menu and populates its info labels
    :param gui_url:The URL of the menu or file this item links to
    :param details:Data such as info labels
    :param extra_data:Data such as stream info
    :param context:The context menu
    :param folder:Is it a folder or file
    :param index:Index in the list
    :type gui_url:str
    :type details:Union[str,object]
    :type extra_data:Union[str,object]
    :type context:
    :type folder:bool
    :type index:int
    :rtype:bool
    :return: Did the item successfully add
    """
    try:
        tbi = ""
        tp = 'Video'
        link_url = ""

        # do this before so it'll log
        # use the year as a fallback in case the date is unavailable
        if details.get('date', '') == '':
            if details.get('aired', '') != '':
                f_data = str(details['aired']).split('-')  # aired y-m-d
                if len(f_data) == 3:
                    if len(f_data[2]) == 1:
                        f_data[2] = '0' + f_data[2]
                    if len(f_data[1]) == 1:
                        f_data[1] = '0' + f_data[1]
                    details['date'] = f_data[2] + '.' + f_data[1] + '.' + f_data[0]  # date d.m.y
                    details['aired'] = f_data[0] + '-' + f_data[1] + '-' + f_data[2]  # aired y-m-d
            elif details.get('year', '') != '' and details.get('year', '0') != 0:
                details['date'] = '01.01.' + str(details['year'])  # date d.m.y
                f_data = str(details['date']).split('.')
                details['aired'] = f_data[2] + '-' + f_data[1] + '-' + f_data[0]  # aired y-m-d

        if util.__addon__.getSetting("spamLog") == 'true':
            xbmc.log("add_gui_item - url: " + gui_url, xbmc.LOGWARNING)
            util.dump_dictionary(details, 'details')
            util.dump_dictionary(extra_data, 'extra data')

        if extra_data is not None and len(extra_data) > 0:
            if extra_data.get('parameters'):
                for argument, value in extra_data.get('parameters').items():
                    link_url = "%s&%s=%s" % (link_url, argument, util.quote(value))
            tbi = extra_data.get('thumb', '')
            tp = extra_data.get('type', 'Video')

        liz = xbmcgui.ListItem(details.get('title', 'Unknown'))
        if tbi is not None and len(tbi) > 0:
            liz.setArt({'thumb': tbi, 'icon': tbi, 'poster': tbi})

        if extra_data is not None and len(extra_data) > 0:
            liz.setUniqueIDs({'anidb': extra_data.get('serie_id', 0)})
            liz.setRating("anidb", details.get('rating', 0), details.get('votes', 0), True)
            actors = extra_data.get('actors', None)
            if actors is not None:
                if len(actors) > 0:
                    try:
                        liz.setCast(actors)
                        details.pop('cast', None)
                        details.pop('castandrole', None)
                    except:
                        pass
        # Set the properties of the item, such as summary, name, season, etc
        liz.setInfo(type=tp, infoLabels=details)

        # TODO Refactor this out into the above method
        # For all video items
        if not folder:
            # liz.setProperty('IsPlayable', 'true')
            liz.setProperty('sorttitle', details.get('sorttitle', details.get('title', 'Unknown')))
            if extra_data and len(extra_data) > 0:
                if extra_data.get('type', 'video').lower() == "video":
                    liz.setProperty('TotalTime', str(extra_data['VideoStreams'][0].get('duration', 0)))
                    if util.__addon__.getSetting("file_resume") == "true":
                        liz.setProperty('ResumeTime', str(extra_data.get('resume')))

                    video_codec = extra_data.get('VideoStreams', {})
                    if len(video_codec) > 0:
                        video_codec = video_codec[0]
                        liz.addStreamInfo('video', video_codec)
                        liz.setProperty('VideoResolution', str(video_codec.get('xVideoResolution', '')))
                        liz.setProperty('VideoCodec', video_codec.get('xVideoCodec', ''))
                        liz.setProperty('VideoAspect', str(video_codec.get('aspect', '')))

                    if len(extra_data.get('AudioStreams', {})) > 0:
                        audio = extra_data.get('AudioStreams')
                        liz.setProperty('AudioCodec', audio.get('xAudioCodec', ''))
                        liz.setProperty('AudioChannels', str(audio.get('xAudioChannels', '')))
                        for stream in extra_data['AudioStreams']:
                            if not isinstance(extra_data['AudioStreams'][stream], dict):
                                continue
                            liz.setProperty('AudioCodec.' + str(stream), str(extra_data['AudioStreams'][stream]
                                                                             ['AudioCodec']))
                            liz.setProperty('AudioChannels.' + str(stream), str(extra_data['AudioStreams'][stream]
                                                                                ['AudioChannels']))
                            audio_codec = dict()
                            audio_codec['codec'] = str(extra_data['AudioStreams'][stream]['AudioCodec'])
                            audio_codec['channels'] = int(extra_data['AudioStreams'][stream]['AudioChannels'])
                            audio_codec['language'] = str(extra_data['AudioStreams'][stream]['AudioLanguage'])
                            liz.addStreamInfo('audio', audio_codec)

                    if len(extra_data.get('SubStreams', {})) > 0:
                        for stream2 in extra_data['SubStreams']:
                            liz.setProperty('SubtitleLanguage.' + str(stream2), str(extra_data['SubStreams'][stream2]
                                                                                    ['SubtitleLanguage']))
                            subtitle_codec = dict()
                            subtitle_codec['language'] = str(extra_data['SubStreams'][stream2]['SubtitleLanguage'])
                            liz.addStreamInfo('subtitle', subtitle_codec)

            # UMS/PSM Jumpy plugin require 'path' to play video
            part_temp = util.parseParameters(input_string=gui_url)
            liz.setProperty('path', str(part_temp.get('file', 'empty')))

        if extra_data and len(extra_data) > 0:
            if extra_data.get('source') == 'serie' or extra_data.get('source') == 'group':
                # Then set the number of watched and unwatched, which will be displayed per season
                liz.setProperty('TotalEpisodes', str(extra_data['TotalEpisodes']))
                liz.setProperty('WatchedEpisodes', str(extra_data['WatchedEpisodes']))
                liz.setProperty('UnWatchedEpisodes', str(extra_data['UnWatchedEpisodes']))

                if extra_data.get('partialTV') == 1:
                    total = str(extra_data['TotalEpisodes'])
                    watched = str(extra_data['WatchedEpisodes'])
                    if sys.version_info < (3, 0):
                        if unicode(total).isnumeric() and unicode(watched).isnumeric():
                            liz.setProperty('TotalTime', total)
                            liz.setProperty('ResumeTime', watched)
                        else:
                            liz.setProperty('TotalTime', '100')
                            liz.setProperty('ResumeTime', '50')
                    else:
                        if total.isnumeric() and watched.isnumeric():
                            liz.setProperty('TotalTime', total)
                            liz.setProperty('ResumeTime', watched)
                        else:
                            liz.setProperty('TotalTime', '100')
                            liz.setProperty('ResumeTime', '50')

            if extra_data.get('thumb'):
                liz.setArt({"thumb": extra_data.get('thumb', '')})
                liz.setArt({"icon": extra_data.get('thumb', '')})
                liz.setArt({"poster": extra_data.get('thumb', '')})
            if extra_data.get('fanart_image'):
                liz.setArt({"fanart": extra_data.get('fanart_image', '')})
                liz.setArt({"clearart": extra_data.get('fanart_image', '')})
            if extra_data.get('banner'):
                liz.setArt({'banner': extra_data.get('banner', '')})
            if extra_data.get('season_thumb'):
                liz.setArt({'seasonThumb': extra_data.get('season_thumb', '')})

        if context is None:
            if extra_data and len(extra_data) > 0:
                context = []
                url_peep_base = sys.argv[0]

                # menu for episode
                if extra_data.get('source', 'none') == 'ep':
                    series_id = extra_data.get('serie_id', 0)
                    ep_id = extra_data.get('ep_id', 0)
                    file_id = extra_data.get('file_id', 0)
                    url_peep = url_peep_base
                    url_peep = util.set_parameter(url_peep, 'mode', 1)
                    url_peep = util.set_parameter(url_peep, 'serie_id', str(series_id))
                    url_peep = util.set_parameter(url_peep, 'ep_id', str(ep_id))
                    url_peep = util.set_parameter(url_peep, 'ui_index', str(index))
                    url_peep = util.set_parameter(url_peep, 'file_id', str(file_id))

                    # Play and Watch
                    if util.__addon__.getSetting('context_show_play_no_watch') == 'true':
                        context.append((util.__addon__.getLocalizedString(30132), 'RunPlugin(%s&cmd=no_mark)' % url_peep))

                    if util.__addon__.getSetting('context_pick_file') == 'true':
                        context.append((util.__addon__.getLocalizedString(30133), 'RunPlugin(%s&cmd=pickFile)' % url_peep))

                    if extra_data.get('jmmepisodeid') != '':
                        if util.__addon__.getSetting('context_krypton_watched') == 'true':
                            if details.get('playcount', 0) == 0:
                                context.append((util.__addon__.getLocalizedString(30128), 'RunPlugin(%s&cmd=watched)' % url_peep))
                            else:
                                context.append((util.__addon__.getLocalizedString(30129), 'RunPlugin(%s&cmd=unwatched)' % url_peep))
                        else:
                            context.append((util.__addon__.getLocalizedString(30128), 'RunPlugin(%s&cmd=watched)' % url_peep))
                            context.append((util.__addon__.getLocalizedString(30129), 'RunPlugin(%s&cmd=unwatched)' % url_peep))

                    if util.__addon__.getSetting('context_playlist') == 'true':
                        context.append((util.__addon__.getLocalizedString(30130), 'RunPlugin(%s&cmd=createPlaylist)' % url_peep))

                    # Vote
                    if util.__addon__.getSetting('context_show_vote_Episode') == 'true' and ep_id != '':
                        context.append((util.__addon__.getLocalizedString(30125), 'RunPlugin(%s&cmd=voteEp)' % url_peep))
                    if util.__addon__.getSetting('context_show_vote_Series') == 'true' and series_id != '':
                        context.append((util.__addon__.getLocalizedString(30124), 'RunPlugin(%s&cmd=voteSer)' % url_peep))

                    # Metadata
                    if util.__addon__.getSetting('context_show_info') == 'true':
                        context.append((util.__addon__.getLocalizedString(30123), 'Action(Info)'))

                    if util.__addon__.getSetting('context_view_cast') == 'true':
                        if series_id != '':
                            context.append((util.__addon__.getLocalizedString(30134), 'ActivateWindow(Videos, %s&cmd=viewCast)' % url_peep))
                    if util.__addon__.getSetting('context_refresh') == 'true':
                        context.append((util.__addon__.getLocalizedString(30131), 'RunPlugin(%s&cmd=refresh)' % url_peep))

        liz.addContextMenuItems(context)
        liz.select(force_select)
        listitems.append((gui_url, liz, folder))
        return liz
    except Exception as e:
        util.error("util.error during add_gui_item", str(e))


def set_watch_flag(extra_data, details):
    """
    Set the flag icon for the list item to the desired state based on watched episodes
    Args:
        extra_data: the extra_data dict
        details: the details dict
    """
    # Set up overlays for watched and unwatched episodes
    if extra_data['WatchedEpisodes'] == 0:
        details['playcount'] = 0
    elif extra_data['UnWatchedEpisodes'] == 0:
        details['playcount'] = 1
    else:
        extra_data['partialTV'] = 1


def get_title(data):
    """
    Get the new title
    Args:
        data: json node containing the title

    Returns: string of the desired title

    """
    try:
        if 'titles' not in data or util.__addon__.getSetting('useutil._server_title') == 'true':
            return util.encode(data.get('name', ''))
        # xbmc.log(data.get('title', 'Unknown'))
        title = util.encode(data.get('name', '').lower())
        if title == 'ova' or title == 'ovas' \
                or title == 'episode' or title == 'episodes' \
                or title == 'special' or title == 'specials' \
                or title == 'parody' or title == 'parodies' \
                or title == 'credit' or title == 'credits' \
                or title == 'trailer' or title == 'trailers' \
                or title == 'other' or title == 'others':
            return util.encode(data.get('name', ''))

        lang = util.__addon__.getSetting("displaylang")
        title_type = util.__addon__.getSetting("title_type")
        try:
            for titleTag in data.get("titles", []):
                if titleTag.get("Type", "").lower() == title_type.lower():
                    if titleTag.get("Language", "").lower() == lang.lower():
                        if util.encode(titleTag.get("Title", "")) == "":
                            continue
                        return util.encode(titleTag.get("Title", ""))
            # fallback on language any title
            for titleTag in data.get("titles", []):
                if titleTag.get("Type", "").lower() != 'short':
                    if titleTag.get("Language", "").lower() == lang.lower():
                        if util.encode(titleTag.get("Title", "")) == "":
                            continue
                        return util.encode(titleTag.get("Title", ""))
            # fallback on x-jat main title
            for titleTag in data.get("titles", []):
                if titleTag.get("Type", "").lower() == 'main':
                    if titleTag.get("Language", "").lower() == "x-jat":
                        if util.encode(titleTag.get("Title", "")) == "":
                            continue
                        return util.encode(titleTag.get("Title", ""))
            # fallback on directory title
            return util.encode(data.get('name', ''))
        except Exception as expc:
            util.error('util.error thrown on getting title', str(expc))
            return util.encode(data.get('name', ''))
    except Exception as exw:
        util.error("get_title Exception", str(exw))
        return 'util.error'


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
        if len(tag_node) > 0:
            temp_genres = []
            for tag in tag_node:
                if isinstance(tag, str) or isinstance(tag, unicode):
                    temp_genres.append(tag)
                else:
                    temp_genre = util.encode(tag["tag"]).strip()
                    temp_genres.append(temp_genre)
            temp_genre = " | ".join(temp_genres)
            return temp_genre
        else:
            return ''
    except Exception as exc:
        util.error('util.error generating tags', str(exc))
        return ''


def get_cast_and_role_new(data):
    """
    Get cast from the json and arrange in the new setCast format
    Args:
        data: json node containing 'roles'

    Returns: a list of dictionaries for the cast
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char.get("character", "")
            char_seiyuuname = char.get("staff", "")
            char_seiyuupic = util._server_ + char.get("character_image", "")

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


def get_cast_and_role(data):
    """
    Get cast from the json and arrange in the new setCast format
    Args:
        data: json node containing 'roles'

    Returns: a list of dictionaries for the cast
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char["role"]
            char_seiyuuname = char['name']
            char_seiyuupic = char["rolepic"]

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

    result_list = []
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
        result_list.append(list_cast)
        result_list.append(list_cast_and_role)
    return result_list


# region Adding items to list/menu:

def add_raw_files(node):
    """
    adding raw_file item to listitem of kodi
    :param node: node containing raw_file
    :return: add item to listitem
    """
    try:
        name = util.encode(node.get("filename", ''))
        file_id = node["id"]
        key = node["url"]
        raw_url = util._server_ + "/api/file?id=" + str(file_id)
        title = util.os.path.split(str(name))[1]
        thumb = util._server_ + "/image/support/plex_others.png"
        liz = xbmcgui.ListItem(label=title, label2=title, path=raw_url)
        liz.setArt({'thumb': thumb, 'poster': thumb, 'icon': 'DefaultVideo.png'})
        liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
        u = sys.argv[0]
        u = util.set_parameter(u, 'url', raw_url)
        u = util.set_parameter(u, 'mode', 1)
        u = util.set_parameter(u, 'name', util.quote_plus(title))
        u = util.set_parameter(u, 'raw_id', file_id)
        u = util.set_parameter(u, 'type', "raw")
        u = util.set_parameter(u, 'file', key)
        u = util.set_parameter(u, 'ep_id', '0')
        u = util.set_parameter(u, 'vl', node["import_folder_id"])
        context = [(util.__addon__.getLocalizedString(30120), 'RunPlugin(%s&cmd=rescan)' % u),
                   (util.__addon__.getLocalizedString(30121), 'RunPlugin(%s&cmd=rehash)' % u),
                   (util.__addon__.getLocalizedString(30122), 'RunPlugin(%s&cmd=missing)' % u)]
        liz.addContextMenuItems(context)
        listitems.append((u, liz, False))
    except:  # Sometimes a file is deleted or invalid, but we should just skip it
        pass


def add_content_typ_dir(name, serie_id):
    """
    Adding directories for given types of content inside series (ex. episodes, credits)
    :param name: name of directory
    :param serie_id: id that the content belong too
    :return: add new directory
    """
    dir_url = util._server_ + "/api/serie"
    dir_url = util.set_parameter(dir_url, 'id', str(serie_id))
    dir_url = util.set_parameter(dir_url, 'level', 4)
    title = str(name)
    thumb = util._server_ + "/api/image/support/"

    if title == "Credit":
        thumb += "plex_credits.png"
    elif title == "Movie":
        thumb += "plex_movies.png"
    elif title == "Ova":
        thumb += "plex_ovas.png"
    elif title == "Other":
        thumb += "plex_others.png"
    elif title == "Episode":
        thumb += "plex_episodes.png"
    elif title == "TV Episode":
        thumb += "plex_tvepisodes.png"
    elif title == "Web Clip":
        thumb += "plex_webclips.png"
    elif title == "Episode":
        thumb += "plex_episodes.png"
    elif title == "Parody":
        thumb += "plex_parodies.png"
    elif title == "Special":
        thumb += "plex_specials.png"
    elif title == "Trailer":
        thumb += "plex_trailers.png"
    elif title == "Misc":
        thumb += "plex_misc.png"
    else:
        thumb += "plex_others.png"

    liz = xbmcgui.ListItem(label=title, label2=title, path=dir_url)
    liz.setArt({'thumb': thumb, 'poster': thumb, 'icon': 'DefaultVideo.png'})
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
    u = sys.argv[0]
    u = util.set_parameter(u, 'url', dir_url)
    u = util.set_parameter(u, 'mode', str(6))
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    u = util.set_parameter(u, 'type', name)
    listitems.append((u, liz, True))


def add_serie_item(node, parent_title, destination_playlist=False):
    """
    Processing serie/content_directory 'node' into episode list
    :param node:
    :param parent_title:
    :param destination_playlist:
    :return:
    """
    # xbmcgui.Dialog().ok('series', 'series')
    temp_genre = ''
    if 'tags' in node:
        temp_genre = get_tags(node.get("tags", {}))

    watched_sizes = node.get("watched_sizes", {})
    if len(watched_sizes) > 0:
        watched = util.safeInt(watched_sizes.get("Episodes", 0))
        if not util.get_kodi_setting_bool("ignore_specials_watched"):
            watched += util.safeInt(watched_sizes.get("Specials", 0))
    else:
        watched = util.safeInt(node.get("watchedsize", ''))

    list_cast = []
    list_cast_and_role = []
    actors = []
    if len(list_cast) == 0 and 'roles' in node:
        cast_nodes = node.get("roles", {})
        if len(cast_nodes) > 0:
            if cast_nodes[0].get("character", "") != "":
                result_list = get_cast_and_role_new(cast_nodes)
            else:
                result_list = get_cast_and_role(cast_nodes)
            actors = result_list
            if result_list is not None:
                result_list = convert_cast_and_role_to_legacy(result_list)
                list_cast = result_list[0]
                list_cast_and_role = result_list[1]

    if util.__addon__.getSetting("local_total") == "true":
        local_sizes = node.get("local_sizes", {})
        if len(local_sizes) > 0:
            total = util.safeInt(local_sizes.get("Episodes", 0)) + util.safeInt(local_sizes.get("Specials", 0))
        else:
            total = util.safeInt(node.get("localsize", ''))
    else:
        sizes = node.get("total_sizes", {})
        if len(sizes) > 0:
            total = util.safeInt(sizes.get("Episodes", 0)) + util.safeInt(sizes.get("Specials", 0))
        else:
            total = util.safeInt(node.get("localsize", ''))

    if watched > total:
        watched = total

    title = get_title(node)
    if "userrating" in node:
        userrating = str(node.get("userrating", '0')).replace(',', '.')
    else:
        userrating = 0.0

    # filter out invalid date
    air = node.get('air', '')
    if air != '':
        # air=0001-01-01
        if air == '0001-01-01' or air == '01-01-0001':
            air = ''

    details = {
        'mediatype':        'episode',
        'title':            title,
        'parenttitle':      util.encode(parent_title),
        'genre':            temp_genre,
        'year':             node.get("year", ''),
        'episode':          total,
        'season':           util.safeInt(node.get("season", '1')),
        # 'count'        : count,
        'size':             total,
        'rating':           float(str(node.get("rating", '0')).replace(',', '.')),
        'userrating':       float(userrating),
        'playcount':        watched,
        'cast':             list_cast,  # cast : list (Michal C. Hall,
        'castandrole':      list_cast_and_role,
        # director       : string (Dagur Kari,
        # 'mpaa':             directory.get('contentRating', ''),
        'plot':             util.remove_anidb_links(util.encode(node.get("summary", '...'))),
        # 'plotoutline'  : plotoutline,
        'originaltitle':    title,
        'sorttitle':        title,
        # 'Duration'     : duration,
        # 'Studio'       : studio, < ---
        # 'Tagline'      : tagline,
        # 'Writer'       : writer,
        # 'tvshowtitle'  : tvshowtitle,
        'tvshowname':       title,
        # 'premiered'    : premiered,
        # 'Status'       : status,
        # code           : string (tt0110293, - IMDb code
        'aired':            str(air),
        # credits        : string (Andy Kaufman, - writing credits
        # 'Lastplayed'   : lastplayed,
        'votes':            node.get('votes', 0),
        # trailer        : string (/home/user/trailer.avi,
        'dateadded':        node.get('added', '')
    }

    directory_type = str(node.get('type', ''))
    key_id = str(node.get('id', ''))
    key = util._server_ + "/api/serie"
    key = util.set_parameter(key, 'id', key_id)
    key = util.set_parameter(key, 'level', 2)
    key = util.set_parameter(key, 'tagfilter', __tagSettingFlags__)
    if util.__addon__.getSetting('request_nocast') == 'true':
        key = util.set_parameter(key, 'nocast', 1)

    thumb = ''
    if len(node["art"]["thumb"]) > 0:
        thumb = node["art"]["thumb"][0]["url"]
        if thumb is not None and ":" not in thumb:
            thumb = util._server_ + thumb
    fanart = ''
    if len(node["art"]["fanart"]) > 0:
        fanart = node["art"]["fanart"][0]["url"]
        if fanart is not None and ":" not in fanart:
            fanart = util._server_ + fanart
    banner = ''
    if len(node["art"]["banner"]) > 0:
        banner = node["art"]["banner"][0]["url"]
        if banner is not None and ":" not in banner:
            banner = util._server_ + banner

    extra_data = {
        'type':                 'video',
        'source':               directory_type,
        'UnWatchedEpisodes':    int(total) - watched,
        'WatchedEpisodes':      watched,
        'TotalEpisodes':        total,
        'thumb':                thumb,
        'fanart_image':         fanart,
        'banner':               banner,
        'key':                  key,
        'actors':               actors,
        'serie_id':             key_id
    }

    serie_url = key
    set_watch_flag(extra_data, details)
    use_mode = 5
    if key_id == '-1' or key_id == '0':
        use_mode = 0

    u = sys.argv[0]
    u = util.set_parameter(u, 'url', serie_url)
    u = util.set_parameter(u, 'mode', use_mode)
    u = util.set_parameter(u, 'movie', node.get('ismovie', '0'))

    context = []
    url_peep = sys.argv[0]
    url_peep = util.set_parameter(url_peep, 'mode', 1)
    url_peep = util.set_parameter(url_peep, 'serie_id', key_id)

    # Watch
    context.append((util.__addon__.getLocalizedString(30126), 'RunPlugin(%s&cmd=watched)' % url_peep))
    context.append((util.__addon__.getLocalizedString(30127), 'RunPlugin(%s&cmd=unwatched)' % url_peep))

    # Vote
    if util.__addon__.getSetting('context_show_vote_Series') == 'true':
        context.append((util.__addon__.getLocalizedString(30124), 'RunPlugin(%s&cmd=voteSer)' % url_peep))

    # Metadata
    if util.__addon__.getSetting('context_show_info') == 'true':
        context.append((util.__addon__.getLocalizedString(30123), 'Action(Info)'))

    if util.__addon__.getSetting('context_view_cast') == 'true':
        context.append((util.__addon__.getLocalizedString(30134), 'ActivateWindow(Videos, %s&cmd=viewCast)' % url_peep))

    if util.__addon__.getSetting('context_refresh') == 'true':
        context.append((util.__addon__.getLocalizedString(30131), 'RunPlugin(%s&cmd=refresh)' % url_peep))

    if destination_playlist:
        return details
    else:
        add_gui_item(u, details, extra_data, context)


def add_group_item(node, parent_title, filter_id, is_filter=False):
    """
    Processing group 'node' into series (serie grouping)
    :param node:
    :param parent_title:
    :param filter_id:
    :param is_filter:
    :return:
    """

    temp_genre = get_tags(node.get("tags", {}))
    title = get_title(node)

    watched_sizes = node.get("watched_sizes", {})
    if len(watched_sizes) > 0:
        watched = util.safeInt(watched_sizes.get("Episodes", 0))
        if not util.get_kodi_setting_bool("ignore_specials_watched"):
            watched += util.safeInt(watched_sizes.get("Specials", 0))
    else:
        watched = util.safeInt(node.get("watchedsize", ''))

    if util.__addon__.getSetting("local_total") == "true":
        local_sizes = node.get("local_sizes", {})
        if len(local_sizes) > 0:
            total = util.safeInt(local_sizes.get("Episodes", 0)) + util.safeInt(local_sizes.get("Specials", 0))
        else:
            total = util.safeInt(node.get("localsize", ''))
    else:
        sizes = node.get("total_sizes", {})
        if len(sizes) > 0:
            total = util.safeInt(sizes.get("Episodes", 0)) + util.safeInt(sizes.get("Specials", 0))
        else:
            total = util.safeInt(node.get("localsize", ''))

    if watched > total:
        watched = total

    content_type = node.get("type", '') if not is_filter else "filter"

    # filter out invalid date
    air = node.get('air', '')
    if air != '':
        # air=0001-01-01
        if air == '0001-01-01' or air == '01-01-0001':
            air = ''

    details = {
        'mediatype':        'tvshow',
        'title':            title,
        'parenttitle':      util.encode(parent_title),
        'genre':            temp_genre,
        'year':             node.get('year', ''),
        'episode':          total,
        'season':           util.safeInt(node.get('season', '1')),
        'size':             total,
        'rating':           float(str(node.get('rating', '0')).replace(',', '.')),
        'userrating':       float(str(node.get('userrating', '0')).replace(',', '.')),
        'playcount':        watched,
        'plot':             util.remove_anidb_links(util.encode(node.get('summary', '...'))),
        'originaltitle':    title,
        'sorttitle':        title,
        'tvshowname':       title,
        'dateadded':        node.get('added', ''),
        'aired':            str(air),
    }

    key_id = str(node.get("id", ''))
    if is_filter:
        key = util._server_ + "/api/filter"
    else:
        key = util._server_ + "/api/group"
    key = util.set_parameter(key, 'id', key_id)
    key = util.set_parameter(key, 'filter', filter_id)
    key = util.set_parameter(key, 'level', 1)
    key = util.set_parameter(key, 'tagfilter', __tagSettingFlags__)
    if util.__addon__.getSetting('request_nocast') == 'true':
        key = util.set_parameter(key, 'nocast', 1)

    thumb = ''
    if len(node["art"]["thumb"]) > 0:
        thumb = node["art"]["thumb"][0]["url"]
        if thumb is not None and ":" not in thumb:
            thumb = util._server_ + thumb
    fanart = ''
    if len(node["art"]["fanart"]) > 0:
        fanart = node["art"]["fanart"][0]["url"]
        if fanart is not None and ":" not in fanart:
            fanart = util._server_ + fanart
    banner = ''
    if len(node["art"]["banner"]) > 0:
        banner = node["art"]["banner"][0]["url"]
        if banner is not None and ":" not in banner:
            banner = util._server_ + banner

    extra_data = {
        'type':                 'video',
        'source':               content_type,
        'thumb':                thumb,
        'fanart_image':         fanart,
        'banner':               banner,
        'key':                  key,
        'group_id':             key_id,
        'WatchedEpisodes':      watched,
        'TotalEpisodes':        total,
        'UnWatchedEpisodes':    total - watched
    }

    group_url = key
    set_watch_flag(extra_data, details)
    use_mode = 4 if not is_filter else 4
    if key_id == '-1' or key_id == '0':
        use_mode = 0

    u = sys.argv[0]
    u = util.set_parameter(u, 'url', group_url)
    u = util.set_parameter(u, 'mode', str(use_mode))
    if filter_id != '':
        u = util.set_parameter(u, 'filter', filter_id)
    else:
        u = util.set_parameter(u, 'filter', None)


    url_peep = sys.argv[0]
    url_peep = util.set_parameter(url_peep, 'mode', 1)
    url_peep = util.set_parameter(url_peep, 'group_id', key_id)

    context = []
    # Watch
    context.append((util.__addon__.getLocalizedString(30126), 'RunPlugin(%s&cmd=watched)' % url_peep))
    context.append((util.__addon__.getLocalizedString(30127), 'RunPlugin(%s&cmd=unwatched)' % url_peep))

    # Metadata
    if util.__addon__.getSetting('context_show_info') == 'true' and not is_filter:
        context.append((util.__addon__.getLocalizedString(30123), 'Action(Info)'))

    if util.__addon__.getSetting('context_refresh') == 'true':
        context.append((util.__addon__.getLocalizedString(30131), 'RunPlugin(%s&cmd=refresh)' % url_peep))

    add_gui_item(u, details, extra_data, context)


def add_filter_item(menu):
    """
    adds a filter item from json
    :param menu: json tree
    """
    use_mode = 4
    key = menu["url"]
    size = util.safeInt(menu.get("size"))
    title = menu['name']

    if title == 'Continue Watching (SYSTEM)':
        title = 'Continue Watching'
    elif title == 'Unsort':
        title = 'Unsorted'
        use_mode = 8

    if util.__addon__.getSetting("spamLog") == "true":
        xbmc.log("build_filters_menu - key = " + key, xbmc.LOGWARNING)

    if util.__addon__.getSetting('request_nocast') == 'true' and title != 'Unsorted':
        key = util.set_parameter(key, 'nocast', 1)
    key = util.set_parameter(key, 'level', 2)
    if title == "Airing Today":
        key = util.set_parameter(key, 'level', 0)
    key = util.set_parameter(key, 'tagfilter', __tagSettingFlags__)
    filter_url = key

    thumb = ''
    try:
        if len(menu["art"]["thumb"]) > 0:
            thumb = menu["art"]["thumb"][0]["url"]
            if ":" not in thumb:
                thumb = util._server_ + thumb
        if "Year" in title or "Airing Today" in title:
            thumb = os.path.join(util._home_, 'resources/media/icons', 'year.png')
        elif "Tag" in title:
            thumb = os.path.join(util._home_, 'resources/media/icons', 'tag.png')
    except:
        if "Year" in title or "Airing Today" in title:
            thumb = os.path.join(util._home_, 'resources/media/icons', 'year.png')
        elif "Tag" in title:
            thumb = os.path.join(util._home_, 'resources/media/icons', 'tag.png')
    fanart = ''
    try:
        if len(menu["art"]["fanart"]) > 0:
            fanart = menu["art"]["fanart"][0]["url"]
            if ":" not in fanart:
                fanart = util._server_ + fanart
    except:
        pass
    banner = ''
    try:
        if len(menu["art"]["banner"]) > 0:
            banner = menu["art"]["banner"][0]["url"]
            if ":" not in banner:
                banner = util._server_ + banner
    except:
        pass

    u = sys.argv[0]
    u = util.set_parameter(u, 'url', filter_url)
    u = util.set_parameter(u, 'mode', use_mode)
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    u = util.set_parameter(u, 'filter_id', menu.get("id", ""))

    liz = xbmcgui.ListItem(label=title, label2=title, path=filter_url)
    liz.setArt({
        'icon': thumb,
        'thumb': thumb,
        'fanart': fanart,
        'poster': thumb,
        'banner': banner,
        'clearart': fanart
    })
    if thumb == '':
        liz.setIconImage('DefaultVideo.png')
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title, "count": size})
    listitems.append((u, liz, True))


def build_filters_menu():
    """
    Builds the list of items (filters) in the Main Menu
    """
    xbmcplugin.setContent(handle, content='tvshows')
    try:
        filters_key = util._server_ + "/api/filter"
        filters_key = util.set_parameter(filters_key, "level", 0)
        json_menu = util.json.loads(util.get_json(filters_key))
        util.set_window_heading(json_menu['name'])
        try:
            menu_append = []
            for menu in json_menu["filters"]:
                title = menu['name']
                if title == 'Seasons':
                    airing = {
                        "name": __addon__.getLocalizedString(30223),
                        "url":  util._server_ + "/api/serie/today"
                    }
                    if util.get_version(util.__addon__.getSetting("ipaddress"),
                                        util.__addon__.getSetting("port")) >= util.LooseVersion("3.8.0.0"):
                        menu_append.append(airing)
                    menu_append.append(menu)
                elif title == 'Tags':
                    menu_append.append(menu)
                elif title == 'Unsort':
                    menu_append.append(menu)
                elif title == 'Years':
                    menu_append.append(menu)
            for menu in json_menu["filters"]:
                title = menu['name']

                if title == 'Unsort':
                    continue
                elif title == 'Tags':
                    continue
                elif title == 'Seasons':
                    continue
                elif title == 'Years':
                    continue
                add_filter_item(menu)

            for menu in menu_append:
                add_filter_item(menu)

        except Exception as e:
            util.error("util.error during build_filters_menu", str(e))
    except Exception as e:
        util.error("Invalid JSON Received in build_filters_menu", str(e))

    # region Start Add_Calendar
    soon_url = util._server_ + "/api/serie/soon"
    title = __addon__.getLocalizedString(30222)
    liz = xbmcgui.ListItem(label=title, label2=title, path=soon_url)
    liz.setArt({"icon": os.path.join(util._home_, 'resources/media/icons', 'year.png'),
                "fanart": os.path.join(util._home_, 'resources/media', 'new-search.jpg')})
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
    u = sys.argv[0]
    u = util.set_parameter(u, 'url', soon_url)
    u = util.set_parameter(u, 'mode', str(9))
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    listitems.append((u, liz, True))
    # endregion

    # region Start Add_NEW_Calendar
    soon_url = util._server_ + "/api/serie/soon"
    title = "Calendar v2"
    liz = xbmcgui.ListItem(label=title, label2=title, path=soon_url)
    liz.setArt({"icon": os.path.join(util._home_, 'resources/media/icons', 'year.png'),
                "fanart": os.path.join(util._home_, 'resources/media', 'new-search.jpg')})
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
    u = sys.argv[0]
    u = util.set_parameter(u, 'url', soon_url)
    u = util.set_parameter(u, 'mode', str(10))
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    listitems.append((u, liz, True))
    # endregion

    # region Start Add_Search
    search_url = util._server_ + "/api/search"
    title = __addon__.getLocalizedString(30221)
    liz = xbmcgui.ListItem(label=title, label2=title, path=search_url)
    liz.setArt({"icon": os.path.join(util._home_, 'resources/media/icons', 'search.png'),
                "fanart": os.path.join(util._home_, 'resources/media', 'new-search.jpg')})
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
    u = sys.argv[0]
    u = util.set_parameter(u, 'url', search_url)
    u = util.set_parameter(u, 'mode', str(3))
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    listitems.append((u, liz, True))
    # endregion

    end_of_directory(False)


def build_groups_menu(params, json_body=None):
    """
    Builds the list of items for Filters and Groups
    Args:
        params:
        json_body: parsing json_file directly, this will skip loading remote url from params
    Returns:

    """
    # xbmcgui.Dialog().ok('MODE=4', 'IN')
    xbmcplugin.setContent(handle, 'tvshows')
    if util.__addon__.getSetting('useutil._server_sort') == 'false':
        xbmcplugin.addSortMethod(handle, 27)  # video title ignore THE
        xbmcplugin.addSortMethod(handle, 3)  # date
        xbmcplugin.addSortMethod(handle, 18)  # rating
        xbmcplugin.addSortMethod(handle, 17)  # year
        xbmcplugin.addSortMethod(handle, 28)  # by MPAA

    try:
        busy.create(util.__addon__.getLocalizedString(30160), util.__addon__.getLocalizedString(30161))
        if json_body is None:
            busy.update(10)
            temp_url = params['url']
            temp_url = util.set_parameter(temp_url, 'nocast', 1)
            temp_url = util.set_parameter(temp_url, 'notag', 1)
            temp_url = util.set_parameter(temp_url, 'level', 0)
            busy.update(20)
            html = util.get_json(temp_url)
            busy.update(50, util.__addon__.getLocalizedString(30162))
            if util.__addon__.getSetting("spamLog") == "true":
                xbmc.log(params['url'], xbmc.LOGWARNING)
                xbmc.log(html, xbmc.LOGWARNING)
            html_body = util.json.loads(html)
            busy.update(70)
            directory_type = html_body['type']
            if directory_type != "filters":
                # level 2 will fill group and series (for filter)
                temp_url = params['url']
                temp_url = util.set_parameter(temp_url, 'level', 2)
                html = util.get_json(temp_url)
                body = util.json.loads(html)
            else:
                # level 1 will fill group and series (for filter)
                temp_url = params['url']
                temp_url = util.set_parameter(temp_url, 'level', 1)
                html = util.get_json(temp_url)
                body = util.json.loads(html)
        else:
            body = json_body
        busy.update(100)
        busy.close()

        # check if this is maybe filter-inception
        try:
            util.set_window_heading(body.get('name', ''))
        except:
            try:  # this might not be a filter
                # it isn't single filter)
                for nest_filter in body:
                    add_group_item(nest_filter, '', body.get('id', ''), True)
                end_of_directory()
                return
            except:
                pass

        try:
            item_count = 0
            parent_title = body.get('name', '')
            directory_type = body.get('type', '')
            filter_id = ''
            if directory_type != 'ep' and directory_type != 'serie':
                if 'filter' in params:
                    filter_id = params['filter']
                    if directory_type == 'filter':
                        filter_id = body.get('id', '')

            if directory_type == 'filter':
                for grp in body["groups"]:
                    if len(grp["series"]) > 0:
                        if len(grp["series"]) == 1:
                            add_serie_item(grp["series"][0], parent_title)
                        else:
                            if json_body is not None:
                                for srg in grp["series"]:
                                    add_serie_item(srg, parent_title)
                            else:
                                add_group_item(grp, parent_title, filter_id)
                    item_count += 1
            elif directory_type == 'filters':
                for flt in body["filters"]:
                    add_group_item(flt, parent_title, filter_id, True)
                    item_count += 1
            elif directory_type == 'group':
                for sers in body['series']:
                    add_serie_item(sers, parent_title)
                    item_count += 1

        except Exception as e:
            util.error("util.error during build_groups_menu", str(e))
    except Exception as e:
        util.error("Invalid JSON Received in build_groups_menu", str(e))
    end_of_directory()


def build_serie_episodes_types(params):
    """
    Builds list items for The Types Menu, or optionally subgroups
    Args:
        params:

    Returns:
    """

    # xbmcgui.Dialog().ok('MODE=5', str(params['url']))
    try:
        html = util.get_json(params['url'])
        if util.__addon__.getSetting("spamLog") == "true":
            xbmc.log(html, xbmc.LOGWARNING)
        body = util.json.loads(html)

        try:
            parent_title = ''
            try:
                parent_title = body.get('name', '')
            except Exception as exc:
                util.error("Unable to get parent title in buildTVSeasons", str(exc))

            content_type = dict()
            if "eps" in body:
                if len(body.get("eps", {})) >= 1:
                    for ep in body["eps"]:
                        if ep["eptype"] not in content_type.keys():
                            content_type[ep["eptype"]] = ep["art"]["thumb"][0]["url"] if len(ep["art"]["thumb"]) > 0 \
                                else ''
            # no matter what type is its only one type, flat directory
            if len(content_type) == 1:
                build_serie_episodes(params)
                return
            else:
                xbmcplugin.setPluginCategory(handle, parent_title)
                xbmcplugin.setContent(handle, 'seasons')
                util.set_window_heading('Types')

                if util.__addon__.getSetting('useutil._server_sort') == 'false':
                    # Apparently date sorting in Kodi has been broken for years
                    xbmcplugin.addSortMethod(handle, 17)  # year
                    xbmcplugin.addSortMethod(handle, 27)  # video title ignore THE
                    xbmcplugin.addSortMethod(handle, 3)  # date
                    xbmcplugin.addSortMethod(handle, 18)  # rating
                    xbmcplugin.addSortMethod(handle, 28)  # by MPAA

                for content in content_type:
                    add_content_typ_dir(content, body.get("id", ''))
                end_of_directory()
                return

        except Exception as exs:
            util.error("util.error during build_serie_episodes_types", str(exs))
    except Exception as exc:
        util.error("Invalid JSON Received in build_serie_episodes_types", str(exc))
    end_of_directory()


def build_serie_episodes(params):
    """
    Load episode information from api, parse them one by one and add to listitem
    :param params:
    :return:
    """

    # xbmcgui.Dialog().ok('MODE=6','IN')
    xbmcplugin.setContent(handle, 'episodes')

    # value to hold position of not seen episode
    next_episode = -1
    episode_count = 0
    is_fake = 0

    busy.create(util.__addon__.getLocalizedString(30160), util.__addon__.getLocalizedString(30163))
    try:
        if 'fake' in params:
            is_fake = params['fake']
        item_count = 0
        html = util.get_json(params['url'])
        busy.update(50, util.__addon__.getLocalizedString(30162))
        body = util.json.loads(html)
        if util.__addon__.getSetting("spamLog") == "true":
            xbmc.log(html, xbmc.LOGWARNING)

        try:
            parent_title = ''
            try:
                parent_title = body.get('name', '')
                util.set_window_heading(parent_title)
            except Exception as exc:
                util.error("Unable to get parent title in buildTVEpisodes", str(exc))

            if util.__addon__.getSetting('useutil._server_sort') == 'false':
                # Set Sort Method
                xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_EPISODE)  # episode
                xbmcplugin.addSortMethod(handle, 3)  # date
                xbmcplugin.addSortMethod(handle, 25)  # video title ignore THE
                xbmcplugin.addSortMethod(handle, 19)  # date added
                xbmcplugin.addSortMethod(handle, 18)  # rating
                xbmcplugin.addSortMethod(handle, 17)  # year
                xbmcplugin.addSortMethod(handle, 29)  # runtime
                xbmcplugin.addSortMethod(handle, 28)  # by MPAA

            skip = util.__addon__.getSetting("skipExtraInfoOnLongSeries") == "true" and len(body.get('eps', {})) > int(
                util.__addon__.getSetting("skipExtraInfoMaxEpisodes"))
            # keep this init out of the loop, as we only provide this once
            temp_genre = ""
            parent_key = ""
            grandparent_title = ""
            list_cast = []
            list_cast_and_role = []
            actors = []
            if not skip:
                if len(list_cast) == 0:
                    cast_nodes = body.get('roles', {})
                    if len(cast_nodes) > 0:
                        if cast_nodes[0].get("character", "") != "":
                            result_list = get_cast_and_role_new(cast_nodes)
                        else:
                            result_list = get_cast_and_role(cast_nodes)
                        actors = result_list
                        if result_list is not None:
                            result_list = convert_cast_and_role_to_legacy(result_list)
                            list_cast = result_list[0]
                            list_cast_and_role = result_list[1]

                short_tag = util.__addon__.getSetting("short_tag_list") == "true"
                temp_genre = get_tags(body.get('tags', {}))
                if short_tag:
                    temp_genre = temp_genre[:50]
                parent_key = body.get('id', '')
                grandparent_title = util.encode(body.get('name', ''))

            if len(body.get('eps', {})) <= 0:
                if is_fake == 0:
                    util.error("No episodes in list")
                else:
                    thumb = ''
                    if len(body["art"]["thumb"]) > 0:
                        thumb = body["art"]["thumb"][0]["url"]
                        if thumb is not None and ":" not in thumb:
                            thumb = util._server_ + thumb
                    details = {
                        'mediatype': 'episode',
                        'plot': util.remove_anidb_links(util.encode(body['summary'])),
                        'title': body['name'],
                        'rating': float(str(body.get('rating', '0')).replace(',', '.')),
                        'castandrole': list_cast_and_role,
                        'cast': list_cast,
                        'aired': body['air'],
                        'tvshowtitle': body['name'],
                        'size': util.safeInt(body.get('size', '0')),
                        'genre': "..." if skip else temp_genre,
                        'tagline': "..." if skip else temp_genre
                    }
                    extra_data = {
                        'source': 'ep',
                        'VideoStreams': defaultdict(dict),
                        'thumb': None if skip else thumb,
                    }
                    extra_data['VideoStreams'][0]['duration'] = 0
                    u = sys.argv[0]
                    add_gui_item(u, details, extra_data, None, folder=False, index=int(episode_count - 1))
                    busy.close()
                    end_of_directory()

                    win_id = xbmcgui.getCurrentWindowId()
                    wind = xbmcgui.Window(win_id)
                    xbmc.sleep(1000)
                    control_id = wind.getFocusId()
                    control_list = wind.getControl(control_id)
                    control_list.selectItem(1)

            elif len(body.get('eps', {})) > 0:
                # add item to move to next not played item (not marked as watched)
                if util.__addon__.getSetting("show_continue") == "true":
                    if sys.version_info < (3, 0):
                        if unicode(parent_title).lower() != "unsort":
                            util.addDir("-continue-", '', '7',util._server_ + "/image/support/plex_others.png", "Next episode", "3", "4", str(next_episode))
                    else:
                        if parent_title.lower() != "unsort":
                            util.addDir("-continue-", '', '7',util._server_ + "/image/support/plex_others.png", "Next episode", "3", "4", str(next_episode))
                selected_list_item = False
                for video in body['eps']:
                    item_count += 1
                    # check if episode have files
                    episode_type = True
                    if "type" in params:
                        episode_type = True if str(video['eptype']) == str(params['type']) else False
                    if video['files'] is not None and episode_type:
                        if len(video['files']) > 0:
                            episode_count += 1
                            # Check for empty duration from MediaInfo check fail and handle it properly
                            tmp_duration = 1
                            try:
                                tmp_duration = video['files'][0]['duration']
                            except:
                                pass
                            if tmp_duration == 1:
                                duration = 1
                            else:
                                duration = int(tmp_duration) / 1000

                            if util.__addon__.getSetting('kodi18') == 1:
                                duration = str(datetime.timedelta(seconds=duration))

                            # filter out invalid date
                            air = video.get('air', '')
                            if air != '':
                                # air=0001-01-01
                                if air == '0001-01-01' or air == '01-01-0001':
                                    air = ''
                            title = util.encode(video.get('name', 'Parse util.error'))
                            if title is None:
                                title = 'Episode ' + str(video.get('epnumber', '??'))

                            # Required listItem entries for XBMC
                            details = {
                                'mediatype':     'episode',
                                'plot':          "..." if skip else util.remove_anidb_links(util.encode(video['summary'])),
                                'title':         title,
                                'sorttitle':     str(video.get('epnumber', '')) + " " + title,
                                'parenttitle':   util.encode(parent_title),
                                'rating':        float(str(video.get('rating', '0')).replace(',', '.')),
                                'userrating':    float(str(video.get('UserRating', '0')).replace(',', '.')),
                                # 'studio'      : episode.get('studio',tree.get('studio','')), 'utf-8') ,
                                # This doesn't work, some gremlins be afoot in this code...
                                # it's probably just that it only applies at series level
                                'castandrole':   list_cast_and_role,
                                'cast':          list_cast,
                                # 'director': " / ".join(temp_dir),
                                # 'writer': " / ".join(temp_writer),
                                'genre':         "..." if skip else temp_genre,
                                'duration':      duration,
                                # 'mpaa':          video.get('contentRating', ''), <--
                                'year':          util.safeInt(video.get('year', '')),
                                'tagline':       "..." if skip else temp_genre,
                                'episode':       util.safeInt(video.get('epnumber', '')),
                                'aired':         air,
                                'tvshowtitle':   grandparent_title,
                                'votes':         util.safeInt(video.get('votes', '')),
                                'originaltitle': util.encode(video.get('name', '')),
                                'size': util.safeInt(video['files'][0].get('size', '0')),
                            }

                            season = str(body.get('season', '1'))
                            try:
                                if season != '1':
                                    season = season.split('x')[0]
                            except Exception as w:
                                util.error(w, season)
                            details['season'] = util.safeInt(season)

                            temp_date = str(details['aired']).split('-')
                            if len(temp_date) == 3:  # format is 2016-01-24, we want it 24.01.2016
                                details['date'] = temp_date[1] + '.' + temp_date[2] + '.' + temp_date[0]

                            thumb = ''
                            if len(video["art"]["thumb"]) > 0:
                                thumb = video["art"]["thumb"][0]["url"]
                                if thumb is not None and ":" not in thumb:
                                    thumb = util._server_ + thumb
                            fanart = ''
                            if len(video["art"]["fanart"]) > 0:
                                fanart = video["art"]["fanart"][0]["url"]
                                if fanart is not None and ":" not in fanart:
                                    fanart = util._server_ + fanart
                            banner = ''
                            if len(video["art"]["banner"]) > 0:
                                banner = video["art"]["banner"][0]["url"]
                                if banner is not None and ":" not in banner:
                                    banner = util._server_ + banner

                            key = video["files"][0]["url"]

                            # Extra data required to manage other properties
                            extra_data = {
                                'type':             'video',
                                'source':           'ep',
                                'thumb':            None if skip else thumb,
                                'fanart_image':     None if skip else fanart,
                                'banner':           None if skip else banner,
                                'key':              key,
                                'resume':           int(int(video['files'][0].get('offset', '0')) / 1000),
                                'parentKey':        parent_key,
                                'jmmepisodeid':     util.safeInt(body.get('id', '')),
                                'actors':           actors,
                                'VideoStreams':     defaultdict(dict),
                                'AudioStreams':     defaultdict(dict),
                                'SubStreams':       defaultdict(dict),
                                'ep_id':            util.safeInt(video.get('id', '')),
                                'serie_id':         util.safeInt(body.get('id', '')),
                                'file_id':          video['files'][0].get('offset', '0')
                            }

                            # Information about streams inside video file
                            if len(video["files"][0].get("media", {})) > 0:
                                video_file_information(video['files'][0]['media'], extra_data)

                            # Determine what type of watched flag [overlay] to use
                            if int(util.safeInt(video.get("view", '0'))) > 0:
                                details['playcount'] = 1
                                details['overlay'] = 5
                                # details['lastplayed'] = '2010-10-10 11:00:00'
                            else:
                                details['playcount'] = 0
                                details['overlay'] = 4
                                if next_episode == -1:
                                    next_episode = episode_count - 1

                            select_this_item = False
                            if details['playcount'] == 0:
                                # if there was no other item select this on listitem
                                if not selected_list_item:
                                    select_this_item = True
                                    selected_list_item = True
                                # Hide plot and thumb for unwatched by kodi setting
                                if not util.get_kodi_setting_bool("videolibrary.showunwatchedplots"):
                                    details['plot'] \
                                        = "Hidden due to user setting.\nCheck Show Plot" + \
                                          " for Unwatched Items in the Video Library Settings."
                                    extra_data['thumb'] = thumb
                                    extra_data['fanart_image'] = fanart

                            context = None

                            u = sys.argv[0]
                            u = util.set_parameter(u, 'mode', 1)
                            u = util.set_parameter(u, 'file_id', video["files"][0].get("id", 0))
                            u = util.set_parameter(u, 'ep_id', video.get("id", ''))
                            u = util.set_parameter(u, 'serie_id', body.get("id", ''))
                            u = util.set_parameter(u, 'userrate', details["userrating"])
                            u = util.set_parameter(u, 'ui_index', str(int(episode_count - 1)))

                            add_gui_item(u, details, extra_data, context,
                                         folder=False, index=int(episode_count - 1),
                                         force_select=select_this_item)

        except Exception as exc:
            util.error("util.error during build_serie_episodes", str(exc))
    except Exception as exc:
        util.error("Invalid JSON Received in build_serie_episodes", str(exc))
    if is_fake == 0:
        busy.close()
        end_of_directory()
    # settings / media / videos / {advanced} / Select first unwatched tv show season,episode (always)
    if util.get_kodi_setting_int('videolibrary.tvshowsselectfirstunwatcheditem') > 0 or \
            util.__addon__.getSetting("select_unwatched") == "true":
        try:
            xbmc.sleep(150)
            new_window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            new_control = new_window.getControl(new_window.getFocusId())
            util.move_position_on_list(new_control, next_episode)
        except:
            pass


def build_cast_menu(params):
    """
    Build the cast menu for 3.8.2+
    :param params:
    :return:
    """
    try:
        search_url = util._server_ + "/api/cast/byseries"
        if params.get("serie_id", "") == "":
            return
        search_url = util.set_parameter(search_url, 'id', params.get("serie_id", ""))
        search_url = util.set_parameter(search_url, 'notag', 1)
        search_url = util.set_parameter(search_url, 'level', 0)
        cast_nodes = util.json.loads(util.get_json(search_url))
        if util.__addon__.getSetting("spamLog") == "true":
            util.dump_dictionary(cast_nodes, "cast_nodes")

        base_search_url = util._server_ + "/api/cast/search"
        base_search_url = util.set_parameter(base_search_url, "fuzzy", 0)

        if len(cast_nodes) > 0:
            if cast_nodes[0].get("character", "") == "":
                return

            xbmcplugin.setContent(handle, 'tvshows')
            for cast in cast_nodes:
                character = cast.get(u"character", u"")
                character_image = util._server_ + cast.get("character_image", "")
                character_description = cast.get("character_description")
                staff = cast.get("staff", "")
                staff_image = util._server_ + cast.get("staff_image", "")

                liz = xbmcgui.ListItem(staff)
                new_search_url = util.set_parameter(base_search_url, "query", staff)

                details = {
                    'mediatype': 'episode',
                    'title': staff,
                    'originaltitle': staff,
                    'sorttitle': staff,
                    'genre': character,

                }

                if character_description is not None:
                    character_description = util.remove_anidb_links(character_description)
                    details['plot'] = character_description

                liz.setInfo(type="video", infoLabels=details)

                if staff_image != "":
                    liz.setArt({"thumb": staff_image,
                                "icon": staff_image,
                                "poster": staff_image})
                if character_image != "":
                    liz.setArt({"fanart": character_image})

                u = sys.argv[0]
                u = util.set_parameter(u, 'mode', 1)
                u = util.set_parameter(u, 'name', params.get('name', 'Cast'))
                u = util.set_parameter(u, 'url', new_search_url)
                u = util.set_parameter(u, 'cmd', 'searchCast')

                listitems.append((u, liz, True))

            end_of_directory()
    except:
        util.error("util.error in build_cast_menu")


def build_search_directory():
    """
    Build Search directory 'New Search' and read Search History
    :return:
    """
    items = [{
        "title": __addon__.getLocalizedString(30224),
        "url": util._server_ + "/api/serie",
        "mode": 3,
        "poster": "none",
        "icon": os.path.join(util._home_, 'resources/media/icons', 'search.png'),
        "fanart": os.path.join(util._home_, 'resources/media', 'new-search.jpg'),
        "type": "",
        "plot": "",
        "extras": "true-search"
    }, {
        "title": "[COLOR yellow]Clear Search Terms[/COLOR]",
        "url": "delete-all",
        "mode": 31,
        "poster": "none",
        "icon": os.path.join(util._home_, 'resources/media/icons', 'trash.png'),
        "fanart": os.path.join(util._home_, 'resources/media', 'clear-search.jpg'),
        "type": "",
        "plot": "",
        "extras": ""
    }]

    # read search history
    search_history = search.get_search_history()
    search_history.sort()
    for ss in search_history:
        try:
            if len(ss[0]) > 0:
                items.append({
                    "title": ss[0],
                    "url": util._server_ + "/api/search",
                    "query": ss[0],
                    "mode": 3,
                    "poster": "none",
                    "icon": os.path.join(util._home_, 'resources/media/icons', 'tag.png'),
                    "fanart": os.path.join(util._home_, '', 'fanart.jpg'),
                    "type": "",
                    "plot": "",
                    "extras": "force-search",
                    "extras2": "db-search"
                })
        except:
            pass

    for detail in items:
        u = sys.argv[0]
        u = util.set_parameter(u, 'url', detail['url'])
        u = util.set_parameter(u, 'mode', detail['mode'])
        u = util.set_parameter(u, 'name', util.encode(detail['title']))
        u = util.set_parameter(u, 'extras', detail['extras'])
        if 'query' in detail:
            u = util.set_parameter(u, 'query', detail['query'])
        liz = xbmcgui.ListItem(util.encode(detail['title']))
        liz.setArt({'thumb': detail['icon'],
                    'poster': detail['poster'],
                    'icon': detail['icon'],
                    'fanart': detail['fanart']})
        liz.setInfo(type=detail['type'], infoLabels={"Title": util.encode(detail['title']), "Plot": detail['plot']})
        listitems.append((u, liz, True))
    end_of_directory(False)


def build_serie_soon_new(params):
    """
            Builds the list of items for newCalendar
            Args:
                params:
            Returns:

            """
    try:
        busy.create(util.__addon__.getLocalizedString(30160), util.__addon__.getLocalizedString(30161))
        busy.update(10)
        temp_url = params['url']
        temp_url = util.set_parameter(temp_url, 'nocast', 0)
        temp_url = util.set_parameter(temp_url, 'notag', 0)
        temp_url = util.set_parameter(temp_url, 'level', 0)
        busy.update(20)
        html = util.get_json(temp_url)
        busy.update(50, util.__addon__.getLocalizedString(30162))
        if util.__addon__.getSetting("spamLog") == "true":
            xbmc.log(params['url'], xbmc.LOGWARNING)
            xbmc.log(html, xbmc.LOGWARNING)
        html_body = util.json.loads(html)
        busy.update(70)
        temp_url = params['url']
        temp_url = util.set_parameter(temp_url, 'level', 2)
        html = util.get_json(temp_url)
        body = util.json.loads(html)
        busy.update(100)
        busy.close()

        try:
            window = Calendar(data=body, handle=handle)
            # xbmcplugin.endOfDirectory(int(sys.argv[1]))
            window.doModal()
            del window
            # return
        except Exception as e:
            util.error("util.error during build_serie_soon date_air", str(e))
    except Exception as e:
        util.error("Invalid JSON Received in build_serie_soon", str(e))


def build_serie_soon(params):
    """
        Builds the list of items for Calendar
        Args:
            params:
        Returns:

        """
    xbmcplugin.setContent(handle, 'tvshows')
    if util.__addon__.getSetting('useutil._server_sort') == 'false':
        xbmcplugin.addSortMethod(handle, sortMethod=xbmcplugin.SORT_METHOD_NONE)  # None

    try:
        busy.create(util.__addon__.getLocalizedString(30160), util.__addon__.getLocalizedString(30161))
        busy.update(20)
        temp_url = params['url']
        temp_url = set_parameter(temp_url, 'level', 2)

        busy.update(10)
        temp_url = params['url']
        temp_url = util.set_parameter(temp_url, 'nocast', 0)
        temp_url = util.set_parameter(temp_url, 'notag', 0)
        temp_url = util.set_parameter(temp_url, 'level', 0)
        busy.update(20)
        html = util.get_json(temp_url)
        busy.update(50, util.__addon__.getLocalizedString(30162))
        if util.__addon__.getSetting("spamLog") == "true":
            xbmc.log(params['url'], xbmc.LOGWARNING)
            xbmc.log(html, xbmc.LOGWARNING)
        html_body = util.json.loads(html)
        busy.update(70)
        directory_type = html_body['type']
        temp_url = params['url']
        temp_url = util.set_parameter(temp_url, 'level', 2)
        html = util.get_json(temp_url)
        body = util.json.loads(html)
        busy.update(100)
        busy.close()

        # check if this is maybe filter-inception
        try:
            util.set_window_heading(body.get('name', ''))
        except:
            set_window_heading(__addon__.getLocalizedString(30222))

        try:
            item_count = 0
            parent_title = body.get('name', '')
            used_dates = []
            for sers in body['series']:
                # region add_date
                if sers.get('air', '') in used_dates:
                    pass
                else:
                    used_dates.append(sers.get('air', ''))
                    soon_url = util._server_ + "/api/serie/soon"
                    details = {}
                    details['aired'] = sers.get('air', '')
                    details['title'] = sers.get('air', '')
                    u = sys.argv[0]
                    u = util.set_parameter(u, 'url', soon_url)
                    u = util.set_parameter(u, 'mode', str(0))
                    u = util.set_parameter(u, 'name', util.quote_plus(details.get('title', '')))
                    extra_data = {'type': 'pictures'}
                    add_gui_item(u, details, extra_data)
                # endregion

                add_serie_item(sers, parent_title)
                item_count += 1

        except Exception as e:
            util.error("util.error during build_serie_soon date_air", str(e))
    except Exception as e:
        util.error("Invalid JSON Received in build_serie_soon", str(e))
    end_of_directory()


def search_for(search_url):
    """
    Actually do the search and build the result
    :param search_url: search url with query
    """
    try:
        search_url = util.set_parameter(search_url, 'tags', 2)
        search_url = util.set_parameter(search_url, 'level', 1)
        search_url = util.set_parameter(search_url, 'limit', util.__addon__.getSetting('maxlimit'))
        search_url = util.set_parameter(search_url, 'limit_tag', util.__addon__.getSetting('maxlimit_tag'))
        json_body = util.json.loads(util.get_json(search_url))
        if json_body["groups"][0]["size"] == 0:
            xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % (util.__addon__.getLocalizedString(30180),
                                                                            util.__addon__.getLocalizedString(30181),
                                                                            '!', util.__addon__.getAddonInfo('icon')))
        else:
            build_groups_menu(search_url, json_body)
    except:
        util.error("util.error in findVideo")


def execute_search_and_add_query():
    """
    Build a search query and if its not in Search History add it
    """
    find = util.searchBox()
    # check search history
    if find == '':
        build_search_directory()
        return
    if not search.check_in_database(find):
        # if its not add to history & refresh
        search.add_search_history(find)
        xbmc.executebuiltin('Container.Refresh')
    search_url = util._server_ + "/api/search"
    search_url = util.set_parameter(search_url, "query", find)
    search_for(search_url)


def build_raw_list(params):
    """
    Build list of RawFiles (ex. Unsort)
    :param params: json body with all files to draw
    :return:
    """
    xbmcplugin.setContent(handle, 'files')
    util.set_window_heading('Unsorted')
    try:
        html = util.get_json(params['url'])
        body = util.json.loads(html)
        if util.__addon__.getSetting("spamLog") == "true":
            xbmc.log(html, xbmc.LOGWARNING)

        try:
            for file_body in body:
                add_raw_files(file_body)
        except Exception as exc:
            util.error("util.error during build_raw_list add_raw_files", str(exc))
    except Exception as exc:
        util.error("util.error during build_raw_list", str(exc))

    end_of_directory(False)


def build_network_menu():
    """
    Build fake menu that will alert user about network util.error (unable to connect to api)
    """
    network_url = util._server_ + "/api/version"
    title = "Network connection util.error"
    liz = xbmcgui.ListItem(label=title, label2=title, path=network_url)
    liz.setArt({"icon": os.path.join(util._home_, 'resources/media/icons', 'search.png'),
                "fanart": os.path.join(util._home_, 'resources/media', 'new-search.jpg')})
    liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": title})
    u = sys.argv[0]
    u = util.set_parameter(u, 'url', network_url)
    u = util.set_parameter(u, 'name', util.quote_plus(title))
    listitems.append((u, liz, True))
    end_of_directory(False)

# endregion


# Other functions
def play_video(ep_id, raw_id, movie):
    """
    Plays a file or episode
    Args:
        ep_id: episode id, if applicable for watched status and stream details
        raw_id: file id, that is only used when ep_id = 0
        movie: determinate if played object is movie or episode (ex.Trakt)
    Returns:

    """
    details = {
        'plot':          xbmc.getInfoLabel('ListItem.Plot'),
        'title':         xbmc.getInfoLabel('ListItem.Title'),
        'sorttitle':     xbmc.getInfoLabel('ListItem.Title'),
        'rating':        xbmc.getInfoLabel('ListItem.Rating'),
        'duration':      xbmc.getInfoLabel('ListItem.Duration'),
        'mpaa':          xbmc.getInfoLabel('ListItem.Mpaa'),
        'year':          xbmc.getInfoLabel('ListItem.Year'),
        'tagline':       xbmc.getInfoLabel('ListItem.Tagline'),
        'episode':       xbmc.getInfoLabel('ListItem.Episode'),
        'aired':         xbmc.getInfoLabel('ListItem.Premiered'),
        'tvshowtitle':   xbmc.getInfoLabel('ListItem.TVShowTitle'),
        'votes':         xbmc.getInfoLabel('ListItem.Votes'),
        'originaltitle': xbmc.getInfoLabel('ListItem.OriginalTitle'),
        'size':          xbmc.getInfoLabel('ListItem.Size'),
        'season':        xbmc.getInfoLabel('ListItem.Season'),
    }

    file_id = ''
    file_url = ''
    offset = 0
    item = ''

    try:
        if ep_id != "0":
            episode_url = util._server_ + "/api/ep?id=" + str(ep_id)
            episode_url = util.set_parameter(episode_url, "level", "1")
            html = util.get_json(util.encode(episode_url))
            if util.__addon__.getSetting("spamLog") == "true":
                xbmc.log(html, xbmc.LOGWARNING)
            episode_body = util.json.loads(html)
            if util.__addon__.getSetting("pick_file") == "true":
                file_id = file_list_gui(episode_body)
            else:
                file_id = episode_body["files"][0]["id"]
        else:
            file_id = raw_id

        if file_id is not None and file_id != 0:
            file_url = util._server_ + "/api/file?id=" + str(file_id)
            file_body = util.json.loads(util.get_json(file_url))

            file_url = file_body['url']
            serverpath = file_body.get('server_path', '')
            if serverpath is not None and serverpath != '':
                try:
                    if os.path.isfile(serverpath):
                        if sys.version_info < (3, 0):
                            if unicode(serverpath).startswith('\\\\'):
                                serverpath = "smb:"+serverpath
                        else:
                            if serverpath.startswith('\\\\'):
                                serverpath = "smb:"+serverpath
                        file_url = serverpath
                except:
                    pass

            # Information about streams inside video file
            # Video
            codecs = dict()
            video_file_information(file_body["media"], codecs)

            details['duration'] = file_body.get('duration', 0)
            details['size'] = file_body['size']

            item = xbmcgui.ListItem(details.get('title', 'Unknown'),
                                    thumbnailImage=xbmc.getInfoLabel('ListItem.Thumb'),
                                    path=file_url)
            item.setInfo(type='Video', infoLabels=details)

            # item.setProperty('IsPlayable', 'true')

            if 'offset' in file_body:
                offset = file_body.get('offset', 0)
                if offset != 0:
                    offset = int(offset) / 1000
                    item.setProperty('ResumeTime', str(offset))

            for stream_index in codecs["VideoStreams"]:
                if not isinstance(codecs["VideoStreams"][stream_index], dict):
                    continue
                item.addStreamInfo('video', codecs["VideoStreams"][stream_index])
            for stream_index in codecs["AudioStreams"]:
                if not isinstance(codecs["AudioStreams"][stream_index], dict):
                    continue
                item.addStreamInfo('audio', codecs["AudioStreams"][stream_index])
            for stream_index in codecs["SubStreams"]:
                if not isinstance(codecs["SubStreams"][stream_index], dict):
                    continue
                item.addStreamInfo('subtitle', codecs["SubStreams"][stream_index])
        else:
            if util.__addon__.getSetting("pick_file") == "false":
                util.error("file_id not retrieved")
            return 0
    except Exception as exc:
        util.error('util.error getting episode info', str(exc))

    try:
        player = xbmc.Player()
        player.play(item=file_url, listitem=item)

        if util.__addon__.getSetting("file_resume") == "true":
            if offset > 0:
                for i in range(0, 1000):  # wait up to 10 secs for the video to start playing before we try to seek
                    if not player.isPlayingVideo():  # and not xbmc.abortRequested:
                        xbmc.sleep(100)
                    else:
                        xbmc.Player().seekTime(offset)
                        xbmc.log("-----player: seek_time offset:" + str(offset), xbmc.LOGNOTICE)
                        break

    except Exception as player_ex:
        xbmc.log(str(player_ex), xbmc.LOGWARNING)
        pass

    # wait for player (network issue etc)
    xbmc.sleep(1000)
    mark = float(util.__addon__.getSetting("watched_mark"))
    mark /= 100
    file_fin = False
    trakt_404 = False
    # hack for slow connection and buffering time
    xbmc.sleep(int(util.__addon__.getSetting("player_sleep")))

    try:
        if raw_id == "0":  # skip for raw_file
            clock_tick = -1
            progress = 0
            while player.isPlaying():
                try:
                    if clock_tick == -1:
                        if util.__addon__.getSetting("trakt_scrobble") == "true":
                            if util.__addon__.getSetting("trakt_scrobble_notification") == "true":
                                xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)"
                                                    % ('Trakt.tv', 'Starting Scrobble',
                                                       '', util.__addon__.getAddonInfo('icon')))
                    clock_tick += 1

                    xbmc.sleep(2500)  # 2.5sec this will make the server handle it better
                    total_time = player.getTotalTime()
                    current_time = player.getTime()

                    # region Resume support (work with shoko 3.6.0.7+)
                    # don't sync until the files is playing and more than 10 seconds in
                    # we'll sync the offset if it's set to sync watched states, and leave file_resume to auto resuming
                    if util.__addon__.getSetting("syncwatched") == "true" and current_time > 10:
                        sync_offset(file_id, current_time)
                    # endregion

                    # region Trakt support
                    if util.__addon__.getSetting("trakt_scrobble") == "true":
                        if clock_tick >= 200:
                            clock_tick = 0
                            if ep_id != 0:
                                progress = int((current_time / total_time) * 100)
                                try:
                                    if not trakt_404:
                                        # status: 1-start,2-pause,3-stop
                                        trakt_body = util.json.loads(util.get_json(util._server_ +
                                                                         "/api/ep/scrobble?id=" + str(ep_id) +
                                                                         "&ismovie=" + str(movie) +
                                                                         "&status=" + str(1) +
                                                                         "&progress=" + str(progress)))
                                        if str(trakt_body.get('code', '')) != str(200):
                                            trakt_404 = True
                                except Exception as trakt_ex:
                                    util.dbg(str(trakt_ex))
                                    pass
                    # endregion

                    if (total_time * mark) < current_time:
                        file_fin = True
                    if not player.isPlaying():
                        break
                except:
                    xbmc.sleep(60)
                    if not trakt_404:
                        # send 'pause' to trakt
                        util.json.loads(util.get_json(util._server_ + "/api/ep/scrobble?id=" + str(ep_id) +
                                            "&ismovie=" + str(movie) +
                                            "&status=" + str(2) +
                                            "&progress=" + str(progress)))
                    break
    except Exception as ops_ex:
        util.dbg(ops_ex)
        pass

    if raw_id == "0":  # skip for raw_file
        no_watch_status = False
        if util.__addon__.getSetting('no_mark') != "0":
            no_watch_status = True
            # reset no_mark so next file will mark watched status
            util.__addon__.setSetting('no_mark', '0')

        if file_fin is True:
            if util.__addon__.getSetting("trakt_scrobble") == "true":
                if not trakt_404:
                    util.get_json(util._server_ +
                             "/api/ep/scrobble?id=" + str(ep_id) +
                             "&ismovie=" + str(movie) +
                             "&status=" + str(3) + "&progress=" + str(100))
                    if util.__addon__.getSetting("trakt_scrobble_notification") == "true":
                        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % ('Trakt.tv', 'Stopping scrobble',
                                                                                        '',
                                                                                        util.__addon__.getAddonInfo('icon')))

            if no_watch_status is False:
                return ep_id
    return 0


def play_continue_item():
    """
    Move to next item that was not marked as watched
    Essential information are query from Parameters via util lib
    """
    params = util.parseParameters()
    if 'offset' in params:
        offset = params['offset']
        pos = int(offset)
        if pos == 1:
            xbmcgui.Dialog().ok(util.__addon__.getLocalizedString(30182), util.__addon__.getLocalizedString(30183))
        else:
            wind = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            control_id = wind.getFocusId()
            control_list = wind.getControl(control_id)
            util.move_position_on_list(control_list, pos)
            xbmc.sleep(1000)
    else:
        pass


def vote_series(params):
    """
    Marks a rating for a series
    Args:
        params: must contain anime_id

    """
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1', '0']
    my_vote = xbmcgui.Dialog().select(util.__addon__.getLocalizedString(30184), vote_list)
    if my_vote == -1:
        return
    elif my_vote != 0:
        vote_value = str(vote_list[my_vote])
        # vote_type = str(1)
        series_id = params['serie_id']
        body = '?id=' + series_id + '&score=' + vote_value
        util.get_json(util._server_ + "/api/serie/vote" + body)
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % (util.__addon__.getLocalizedString(30184),
                                                                        util.__addon__.getLocalizedString(30185),
                                                                        vote_value, util.__addon__.getAddonInfo('icon')))


def vote_episode(params):
    """
    Marks a rating for an episode
    Args:
        params: must contain ep_id

    """
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1', '0']
    my_vote = xbmcgui.Dialog().select(util.__addon__.getLocalizedString(30186), vote_list)
    if my_vote == -1:
        return
    elif my_vote != 0:
        vote_value = str(vote_list[my_vote])
        # vote_type = str(4)
        ep_id = params['ep_id']
        body = '?id=' + ep_id + '&score=' + vote_value
        util.get_json(util._server_ + "/api/ep/vote" + body)
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % (util.__addon__.getLocalizedString(30186),
                                                                        util.__addon__.getLocalizedString(30185),
                                                                        vote_value, util.__addon__.getAddonInfo('icon')))


def sync_offset(file_id, current_time):
    """
    sync offset of played file
    :param file_id: id
    :param current_time: current time in seconds
    """

    offset_url = util._server_ + "/api/file/offset"
    offset_body = '"id":' + str(file_id) + ',"offset":' + str(current_time * 1000)
    try:
        util.post_json(offset_url, offset_body)
    except:
        util.error("error Scrobbling.", '', True)


def file_list_gui(ep_body):
    """
    Create GUI with file list to pick
    :param ep_body:
    :return: int (id of picked file or 0 if none)
    """
    pick_filename = []
    get_fileid = []
    if len(ep_body['files']) > 1:
        for body in ep_body['files']:
            filename = os.path.basename(body['filename'])
            pick_filename.append(filename)
            get_fileid.append(str(body['id']))
        my_file = xbmcgui.Dialog().select(util.__addon__.getLocalizedString(30196), pick_filename)
        if my_file > -1:
            return get_fileid[my_file]
        else:
            # cancel -1,0
            return 0
    elif len(ep_body['files']) == 1:
        return ep_body['files'][0]['id']
    else:
        return 0


def watched_mark(params):
    """
    Marks an episode, series, or group as either watched (offset = 0) or unwatched
    Args:
        params: must contain either an episode, series, or group id, and a watched value to mark
    """
    episode_id = params.get('ep_id', '')
    anime_id = params.get('serie_id', '')
    group_id = params.get('group_id', '')
    file_id = params.get('file_id', 0)
    watched = bool(params['watched'])
    key = util._server_ + "/api"

    if watched is True:
        watched_msg = "watched"
        if episode_id != '':
            key += "/ep/watch"
        elif anime_id != '':
            key += "/serie/watch"
        elif group_id != '':
            key += "/group/watch"
    else:
        watched_msg = "unwatched"
        if episode_id != '':
            key += "/ep/unwatch"
        elif anime_id != '':
            key += "/serie/unwatch"
        elif group_id != '':
            key += "/group/unwatch"

    if file_id != 0:
        sync_offset(file_id, 0)

    if util.__addon__.getSetting('log_spam') == 'true':
        xbmc.log('file_d: ' + str(file_id), xbmc.LOGWARNING)
        xbmc.log('epid: ' + str(episode_id), xbmc.LOGWARNING)
        xbmc.log('anime_id: ' + str(anime_id), xbmc.LOGWARNING)
        xbmc.log('group_id: ' + str(group_id), xbmc.LOGWARNING)
        xbmc.log('key: ' + key, xbmc.LOGWARNING)

    # sync mark flags
    sync = util.__addon__.getSetting("syncwatched")
    if sync == "true":
        if episode_id != '':
            body = '?id=' + episode_id
            util.get_json(key + body)
        elif anime_id != '':
            body = '?id=' + anime_id
            util.get_json(key + body)
        elif group_id != '':
            body = '?id=' + group_id
            util.get_json(key + body)
    else:
        xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

    box = util.__addon__.getSetting("watchedbox")
    if box == "true":
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 2000, %s)" % (util.__addon__.getLocalizedString(30187),
                                                                        util.__addon__.getLocalizedString(30188),
                                                                        watched_msg,
                                                                        util.__addon__.getAddonInfo('icon')))
    util.refresh()


def rescan_file(params, rescan):
    """
    Rescans or rehashes a file
    Args:
        params:
        rescan: True to rescan, False to rehash
    """
    vl_id = params.get('vl', '')
    command = 'rehash'
    if rescan:
        command = 'rescan'

    key_url = ""
    if vl_id != '':
        key_url = util._server_ + "/api/" + command + "?id=" + vl_id
    if util.__addon__.getSetting('log_spam') == 'true':
        xbmc.log('vlid: ' + str(vl_id), xbmc.LOGWARNING)
        xbmc.log('key: ' + key_url, xbmc.LOGWARNING)

        util.get_json(key_url)

    xbmc.executebuiltin("XBMC.Notification(%s, %s, 2000, %s)" % (
                util.__addon__.getLocalizedString(30190) if rescan else util.__addon__.getLocalizedString(30189),
                util.__addon__.getLocalizedString(30191), util.__addon__.getAddonInfo('icon')))
    xbmc.sleep(10000)
    util.refresh()


def remove_missing_files():
    """
    Run "remove missing files" on server to remove every file that is not accessible by server
    :return:
    """
    key = util._server_ + "/api/remove_missing_files"

    if util.__addon__.getSetting('log_spam') == 'true':
        xbmc.log('key: ' + key, xbmc.LOGWARNING)

        util.get_json(key)
    xbmc.executebuiltin("XBMC.Notification(%s, %s, 2000, %s)" % (util.__addon__.getLocalizedString(30192),
                                                                 util.__addon__.getLocalizedString(30193),
                                                                 util.__addon__.getAddonInfo('icon')))
    xbmc.sleep(10000)
    util.refresh()


def create_playlist(serie_id):
    """
    Create playlist of all episodes that wasn't watched
    :param serie_id:
    :return:
    """
    serie_url = util._server_ + "/api/serie?id=" + str(serie_id) + "&level=2&nocast=1&notag=1"
    serie_body = util.json.loads(util.get_json(serie_url))
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    item_count = 0
    # TODO sort by epnumber and eptype so it wont get mixed
    if 'eps' in serie_body:
        if len(serie_body['eps']) > 0:
            for serie in serie_body['eps']:
                if len(serie['files']) > 0:
                    if 'view' in serie:
                        if serie['view'] == 1:
                            continue
                    video = serie['files'][0]['url']
                    details = add_serie_item(serie, serie_body['name'], True)
                    liz = xbmcgui.ListItem(details.get('title', 'Unknown'))
                    liz.setInfo(type='Video', infoLabels=details)
                    item_count += 1
                    playlist.add(url=video, listitem=liz, index=item_count)
    if item_count > 0:
        xbmc.Player().play(playlist)


# region Setting up Remote Debug
if util.__addon__.getSetting('remote_debug') == 'true':
    try:
        if has_pydev:
            pydevd.settrace(util.__addon__.getSetting('ide_ip'), port=int(util.__addon__.getSetting('ide_port')),
                            stdoutToServer=True, stderrToServer=True, suspend=False)
        else:
            util.error('pydevd not found, disabling remote_debug')
            util.__addon__.setSetting('remote_debug', 'false')
    except Exception as ex:
        util.error('Unable to start debugger, disabling', str(ex))
        util.__addon__.setSetting('remote_debug', 'false')
# endregion

# Script run from here

global __tagSettingFlags__
__tagSettingFlags__ = util.populate_tag_setting_flags()

if util.__addon__.getSetting('spamLog') == "true":
    util.dump_dictionary(sys.argv, 'sys.argv')

# 3 is not checked
if util.__addon__.getSetting('kodi18') == '3':
    python = xbmcaddon.Addon('xbmc.addon')
    if python is not None:
        # kodi18 return 17.9.701 as for now
        if str(python.getAddonInfo('version')) == '17.9.701':
            util.__addon__.setSetting(id='kodi18', value='1')
        else:
            util.__addon__.setSetting(id='kodi18', value='0')

if util.__addon__.getSetting('wizard') == '0':
    wizard = Wizard(util.__addon__.getLocalizedString(30082))
    wizard.doModal()
    if wizard.setup_ok:
        util.__addon__.setSetting(id='wizard', value='1')
    del wizard

if util.get_server_status(ip=util.__addon__.getSetting('ipaddress'), port=util.__addon__.getSetting('port')) is True:
    if util.valid_user() is True:
        try:
            parameters = util.parseParameters()
        except Exception as exp:
            util.error('valid_userid_1 parseParameters() util.error', str(exp))
            parameters = {'mode': 2}

        if parameters:
            try:
                mode = int(parameters['mode'])
            except Exception as exp:
                util.error('valid_userid set \'mode\' util.error', str(exp) + " parameters: " + str(parameters))
                mode = None
        else:
            mode = None

        try:
            if 'cmd' in parameters:
                cmd = parameters['cmd']
            else:
                cmd = None
        except Exception as exp:
            util.error('valid_userid_2 parseParameters() util.error', str(exp))
            cmd = None
        if cmd is not None:
            if cmd == "voteSer":
                vote_series(parameters)
            elif cmd == "voteEp":
                vote_episode(parameters)
            elif cmd == "viewCast":
                build_cast_menu(parameters)
            elif cmd == "searchCast":
                search_for(parameters.get('url', ''))
            elif cmd == "watched":
                if util.get_kodi_setting_int('videolibrary.tvshowsselectfirstunwatcheditem') == 0 or \
                        util.__addon__.getSetting("select_unwatched") == "true":
                    try:
                        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                        ctl = win.getControl(win.getFocusId())
                        # noinspection PyTypeChecker
                        ui_index = parameters.get('ui_index', '')
                        if ui_index != '':
                            util.move_position_on_list(ctl, int(ui_index) + 1)
                    except Exception as exp:
                        xbmc.log(str(exp), xbmc.LOGWARNING)
                        pass
                parameters['watched'] = True
                watched_mark(parameters)
                if util.__addon__.getSetting("vote_always") == "true":
                    if parameters.get('userrate', 0) == 0:
                        vote_episode(parameters)
            elif cmd == "unwatched":
                parameters['watched'] = False
                watched_mark(parameters)
            elif cmd == "playlist":
                play_continue_item()
            elif cmd == "no_mark":
                util.__addon__.setSetting('no_mark', '1')
                xbmc.executebuiltin('Action(Select)')
            elif cmd == "pickFile":
                if str(parameters['ep_id']) != "0":
                    ep_url = util._server_ + "/api/ep?id=" + str(parameters['ep_id']) + "&level=2"
                    file_list_gui(util.json.loads(util.get_json(ep_url)))
            elif cmd == 'rescan':
                rescan_file(parameters, True)
            elif cmd == 'rehash':
                rescan_file(parameters, False)
            elif cmd == 'missing':
                remove_missing_files()
            elif cmd == 'createPlaylist':
                create_playlist(parameters['serie_id'])
            elif cmd == 'refresh':
                util.refresh()
        else:
            if mode == 0:  # string label
                pass
            elif mode == 1:  # play_file
                try:
                    win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                    ctl = win.getControl(win.getFocusId())
                    if play_video(parameters['ep_id'],
                                  parameters['raw_id'] if 'raw_id' in parameters else "0",
                                  parameters['movie'] if 'movie' in parameters else 0) > 0:
                        # noinspection PyTypeChecker
                        ui_index = parameters.get('ui_index', '')
                        if ui_index != '':
                            util.move_position_on_list(ctl, int(ui_index) + 1)
                        parameters['watched'] = True
                        watched_mark(parameters)

                        if util.__addon__.getSetting('vote_always') == 'true':
                            # convert in case shoko give float
                            if parameters.get('userrate', '0.0') == '0.0':
                                vote_episode(parameters)
                            else:
                                xbmc.log("------- vote_always found 'userrate':" + str(parameters.get('userrate',
                                                                                                      '0.0')),
                                         xbmc.LOGNOTICE)
                except Exception as exp:
                    xbmc.log(str(exp), xbmc.LOGWARNING)
                    pass
            elif mode == 2:  # DIRECTORY
                xbmcgui.Dialog().ok('MODE=2', 'MODE')
            elif mode == 3:  # Search
                try:
                    if parameters['extras'] == "force-search" and 'query' in parameters:
                        url = util._server_ + '/api/search'
                        url = util.set_parameter(url, 'query', parameters['query'])
                        search_for(url)
                    else:
                        xbmcplugin.setContent(int(handle), "movies")
                        execute_search_and_add_query()
                except:
                    build_search_directory()
            elif mode == 4:  # Group/Serie
                try:
                    if has_line_profiler:
                        profiler = line_profiler.LineProfiler()
                        profiler.add_function(build_groups_menu)
                        profiler.enable_by_count()
                    build_groups_menu(parameters)
                finally:
                    if has_line_profiler:
                        profiler.print_stats(open('stats.txt', 'w'))
            elif mode == 5:  # Serie EpisodeTypes (episodes/ovs/credits)
                build_serie_episodes_types(parameters)
            elif mode == 6:  # Serie Episodes (list of episodes)
                build_serie_episodes(parameters)
            elif mode == 7:  # Playlist -continue-
                play_continue_item()
            elif mode == 8:  # File List
                build_raw_list(parameters)
            elif mode == 9:  # Calendar
                build_serie_soon(parameters)
            elif mode == 10:  # newCalendar
                build_serie_soon_new(parameters)
            elif mode == 31:
                search.clear_search_history(parameters)
            else:
                build_filters_menu()
    else:
        util.error(util.__addon__.getLocalizedString(30194), util.__addon__.getLocalizedString(30195))
else:
    util.__addon__.setSetting(id='wizard', value='0')
    build_network_menu()

if util.__addon__.getSetting('remote_debug') == 'true':
    try:
        if has_pydev:
            pydevd.stoptrace()
    except Exception as remote_exc:
        xbmc.log(str(remote_exc), xbmc.LOGWARNING)
        pass
