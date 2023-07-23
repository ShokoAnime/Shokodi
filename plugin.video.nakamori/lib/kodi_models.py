import sys

import xbmc
import xbmcgui
import xbmcplugin

from lib.error_handler import ErrorPriority
from lib.nakamori_utils.globalvars import *
from lib import error_handler as eh


class UniqueIds:
    def __init__(self):
        self.shoko_aid = 0
        self.shoko_eid = 0
        self.anidb_id = 0
        self.tvdb_id = 0

    def get_dict(self):
        ids = dict()
        if self.shoko_aid != 0:
            ids['shoko_aid'] = str(self.shoko_aid)
        if self.shoko_eid != 0:
            ids['shoko_eid'] = str(self.shoko_eid)
        if self.anidb_id != 0:
            ids['anidb'] = str(self.anidb_id)
        if self.tvdb_id != 0:
            ids['tvdb'] = str(self.tvdb_id)

        return ids


class VoteType(object):
    EPISODE = 'episode'
    SERIES = 'series'


class WatchedStatus(object):
    UNWATCHED = 0
    PARTIAL = 1
    WATCHED = 2


class ListItem:
    def __init__(self, label='', label2='', path='', offscreen=False):
        if float(kodi_version) > 18:
            self.list_item = xbmcgui.ListItem(label=label, label2=label2, path=path, offscreen=offscreen)
            self.videoTag = self.list_item.getVideoInfoTag()
        else:
            self.list_item = xbmcgui.ListItem(label, label2, path=path)

    def set_info(self, type, infoLabels):
        if float(kodi_version) > 20:
            if type == 'video':
                try:
                    self.videoTag.setTitle(self.list_item.getLabel())
                    if 'aired' in infoLabels:
                        self.videoTag.setFirstAired(infoLabels['aired'])
                    if 'mediatype' in infoLabels:
                        self.videoTag.setMediaType(infoLabels['mediatype'])
                    if 'path' in infoLabels:
                        self.videoTag.setPath(infoLabels['path'])
                    if 'sorttitle' in infoLabels:
                        self.videoTag.setSortTitle(infoLabels['sorttitle'])
                    if 'originaltitle' in infoLabels:
                        self.videoTag.setOriginalTitle(infoLabels['originaltitle'])
                    if 'plot' in infoLabels:
                        self.videoTag.setPlot(infoLabels['plot'])
                    if 'plotoutline' in infoLabels:
                        self.videoTag.setPlotOutline(infoLabels['plotoutline'])
                    if 'dateadded' in infoLabels:
                        self.videoTag.setDateAdded(infoLabels['dateadded'])
                    if 'year' in infoLabels and infoLabels['year'] is not None and infoLabels['year'] != '':
                        self.videoTag.setYear(int(infoLabels['year']))
                    if 'mpaa' in infoLabels:
                        self.videoTag.setMpaa(infoLabels['mpaa'])
                    if 'duration' in infoLabels:
                        self.videoTag.setDuration(int(infoLabels['duration']))
                    if 'genre' in infoLabels and infoLabels['genre'] is not None and infoLabels['genre'] != '':
                        self.videoTag.setGenres(infoLabels['genre'])
                    if 'tag' in infoLabels:
                        self.videoTag.setTags(infoLabels['tag'])
                    if 'trailer' in infoLabels:
                        self.videoTag.setTrailer(infoLabels['trailer'])
                    if 'tagline' in infoLabels:
                        self.videoTag.setTagLine(infoLabels['tagline'])
                    if 'studio' in infoLabels and infoLabels['studio'] != '':
                        self.videoTag.setStudios([infoLabels['studio']])
                    if 'season' in infoLabels:
                        self.videoTag.setSeason(infoLabels['season'])
                    if 'episode' in infoLabels:
                        self.videoTag.setEpisode(infoLabels['episode'])
                    if 'userrating' in infoLabels:
                        self.videoTag.setUserRating(int(infoLabels['userrating']))
                except:
                    eh.exception(ErrorPriority.HIGHEST)
        else:
            self.list_item.setInfo(type=type, infoLabels=infoLabels)

    def set_path(self, path):
        self.list_item.setPath(path)

    def getPath(self):
        return self.list_item.getPath()

    def set_property(self, property, value):
        self.list_item.setProperty(property, value)

    def add_stream_info(self, type, info):
        if float(kodi_version) > 18:
            video = self.videoTag
            if type == 'video':
                stream = xbmc.VideoStreamDetail(width=int(info['width']), height=int(info['height']),
                                                codec=info['codec'], aspect=float(info['aspect']))
                video.addVideoStream(stream)
            if type == 'audio':
                stream = xbmc.AudioStreamDetail(codec=info['codec'], channels=int(info['channels']),
                                                language=info['language'])
                video.addAudioStream(stream)
            if type == 'subtitle':
                stream = xbmc.SubtitleStreamDetail(language=info['language'])
                video.addSubtitleStream(stream)
        else:
            self.list_item.addStreamInfo(type, info)

    def set_cast(self, cast):
        if len(cast) <= 0:
            return
        if float(kodi_version) > 18:
            actors = []
            for c in cast:
                actors.append(xbmc.Actor(name=c['name'], role=c['role'], thumbnail=c['thumbnail']))
            self.videoTag.setCast(actors)
        else:
            self.list_item.setCast(cast)

    def set_rating(self, type, rating, votes=0, default=True):
        if float(kodi_version) > 18:
            self.videoTag.setRating(type=type, rating=float(rating), votes=votes, isdefault=default)
        else:
            self.list_item.setRating(type=type, rating=rating, votes=votes, defaultt=default)

    def set_unique_ids(self, unique_ids):
        if float(kodi_version) > 18:
            self.videoTag.setUniqueIDs(unique_ids.get_dict())
        else:
            self.list_item.setUniqueIDs(unique_ids.get_dict())

    def add_context_menu_items(self, items):
        self.list_item.addContextMenuItems(items=items)

    def set_art(self, dir_obj):
        """
        Set Art from a Directory object
        :param dir_obj:
        :type dir_obj: Directory
        :return:
        """
        if dir_obj.fanart is not None:
            self.set_fanart(dir_obj.fanart)
        if dir_obj.poster is not None:
            self.set_thumb(dir_obj.poster)
        if dir_obj.banner is not None:
            self.set_banner(dir_obj.banner)
        if dir_obj.icon is not None:
            self.set_icon(dir_obj.icon)
        else:
            if dir_obj.poster is not None:
                self.set_icon(dir_obj.poster)

    def set_icon(self, icon):
        self.list_item.setArt({'icon': icon})

    def set_thumb(self, thumb):
        self.list_item.setArt({'thumb': thumb})
        self.list_item.setArt({'poster': thumb})

    def set_fanart(self, fanart):
        self.list_item.setArt({'fanart': fanart})
        self.list_item.setArt({'clearart': fanart})

    def set_banner(self, banner):
        self.list_item.setArt({'banner': banner})

    def set_watched_flags(self, infolabels, flag, resume_time=0, total_time=0):
        """
        set the needed flags on a listitem for watched or resume icons
        :param self:
        :param infolabels
        :param flag:
        :type flag: WatchedStatus
        :param resume_time: int s
        :return:
        """
        if flag == WatchedStatus.UNWATCHED:
            if float(kodi_version) > 18:
                self.videoTag.setPlaycount(0)
            else:
                infolabels['playcount'] = 0
                infolabels['overlay'] = 4
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))
        elif flag == WatchedStatus.WATCHED:
            if float(kodi_version) > 18:
                self.videoTag.setPlaycount(1)
            else:
                infolabels['playcount'] = 1
                infolabels['overlay'] = 5
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))
        elif flag == WatchedStatus.PARTIAL and plugin_addon.getSetting('file_resume') == 'true':
            if float(kodi_version) > 18:
                self.videoTag.setResumePoint(float(resume_time), float(total_time))
            else:
                eh.exception(ErrorPriority.NORMAL)
                self.list_item.setProperty('ResumeTime', str(resume_time))
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))

    def resume(self):
        resume = self.list_item.getProperty('ResumeTime')
        if resume is None or resume == '':
            return
        self.list_item.setProperty('StartOffset', resume)


class DirectoryListing(object):
    """
    An optimized list to add directory items.
    There may be a speedup by calling `del dir_list`, but Kodi's GC is pretty aggressive
    """
    def __init__(self, content_type='', cache=False):
        self.pending = []
        self.handle = int(sys.argv[1])
        self._cache = cache
        self.success = True
        self._content_type = content_type
        if self._content_type != '':
            xbmcplugin.setContent(self.handle, content_type)
        self._immediate = False
        self._finished = False

    def set_immediate(self, immediate):
        self._immediate = immediate

    def set_cached(self):
        self._cache = True

    def set_content(self, content_type):
        self._content_type = content_type

        if self._content_type != '':
            xbmcplugin.setContent(self.handle, content_type)

    def extend(self, iterable):
        result_list = []
        for item in iterable:
            result = get_tuple(item)
            if result is not None:
                result_list.append(result)
        return self.pending.extend(result_list)

    def append(self, item, folder=True, total_items=0):
        result = get_tuple(item, folder)
        if result is not None:
            if self._immediate:
                if total_items != 0:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2], total_items)
                else:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2])
            else:
                self.pending.append(result)
                return True
        else:
            raise RuntimeError('Attempting to Add Not a ListItem to the List')

    def insert(self, index, obj, folder=True):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = get_tuple(obj, folder)
        return self.pending.insert(index, item)

    def __getitem__(self, item):
        if self._immediate:
            raise RuntimeError('Cannot get items after adding. Immediate mode is enabled')
        return self.pending.__getitem__(item)

    def __setitem__(self, key, value):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = get_tuple(value, True)
        return self.pending.__setitem__(key, item)

    def __delitem__(self, key):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        return self.pending.__delitem__(key)

    def finish(self):
        if self._finished:
            return
        if not self._immediate and len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.pending.__len__())
        if xbmcplugin is not None:
            xbmcplugin.endOfDirectory(self.handle, succeeded=self.success, cacheToDisc=self._cache)
        self._finished = True

    def __del__(self):
        self.finish()


class VideoLibraryItem(object):
    def __init__(self):
        from lib.nakamori_utils import kodi_utils
        import xbmc

        self.dbid = str(xbmc.getInfoLabel('ListItem.DBID'))
        self.media_type = kodi_utils.get_media_type_from_container()

    def vote(self, vote_type):
        if self.dbid == '':
            eh.exception(eh.ErrorPriority.HIGHEST, 'Unable to Vote for Series', 'No ID was found on the object')
            return
        if vote_type == 'series':
            try:
                self._vote_series()
            except:
                eh.exception(eh.ErrorPriority.HIGHEST)
        elif vote_type == self.media_type:
            try:
                self._vote_episode()
            except:
                eh.exception(eh.ErrorPriority.HIGHEST)

    def _vote_series(self):
        from lib.nakamori_utils import kodi_utils

        dbid = self.dbid
        # vote series from inside episode, get and set proper variables so we can continue
        if self.media_type == 'episode':
            method = 'VideoLibrary.GetEpisodeDetails'
            params = {
                "properties": ["uniqueid", "showtitle", "season", "episode", "tvshowid", "userrating"],
                "episodeid": self.dbid
            }

            result = kodi_utils.kodi_jsonrpc(method, params)
            episode_details = result['result']['episodedetails']
            dbid = str(episode_details['tvshowid'])
        # we vote for series from series or episode
        if self.media_type in ('show', 'episode') and self.dbid != '':
            method = 'VideoLibrary.GetTVShowDetails'
            params = {
                "properties": ["uniqueid", "originaltitle", "userrating"],
                "tvshowid": dbid
            }
            # If this fails, it'll throw to the outer section and show a message
            result = kodi_utils.kodi_jsonrpc(method, params)
            tvshow_details = result['result']['tvshowdetails']
            vote_if_no_userrating_or_revote(tvshow_details, VoteType.SERIES)

    def _vote_episode(self):
        from lib.nakamori_utils import kodi_utils

        # vote episode from inside episode
        method = "VideoLibrary.GetEpisodeDetails"
        params = {
            "properties": ["uniqueid", "showtitle", "season", "episode", "tvshowid", "userrating"],
            "episodeid": self.dbid
        }
        result = kodi_utils.kodi_jsonrpc(method, params)
        episode_details = result['result']['episodedetails']
        vote_if_no_userrating_or_revote(episode_details, VoteType.EPISODE)


def get_tuple(item, folder=True):
    if is_listitem(item):
        return item.getPath(), item, folder
    if isinstance(item, tuple):
        if len(item) == 2:
            if not is_listitem(item[0]):
                return None
            return item[0].getPath(), item[0], item[1]
        if len(item) == 3:
            if not is_listitem(item[1]):
                return None
            return item[0], item[1], item[2]
    return None


def is_listitem(item):
    return isinstance(item, xbmcgui.ListItem) or isinstance(item, ListItem)


def vote_if_no_userrating_or_revote(json_node, vote_type=VoteType.EPISODE):
    # TODO Log
    if 'uniqueid' not in json_node:
        raise RuntimeError('Unable to Vote. No uniqueID was found on the object')
    eid = json_node['uniqueid'].get('shoko_eid', 0)
    aid = json_node['uniqueid'].get('shoko_aid', 0)
    _id = eid if vote_type == VoteType.EPISODE else aid

    if json_node.get('userrating', 0) != 0 and not xbmcgui.Dialog().yesno('You already voted',
                                                                          'Your previouse vote was '
                                                                          + str(json_node['userrating'])
                                                                          + '/10\nDo you want to change your vote?'):
        return

    import xbmc
    xbmc.executebuiltin("RunScript(plugin.video.nakamori,/%s/%s/vote)" % (vote_type, _id))
    # TODO return rating from shoko or script and setRating to listItem
