import xbmc
import xbmcgui

from lib.nakamori_utils.globalvars import plugin_addon
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.kodi.kodi_18_proxy import Kodi18Proxy


class Kodi19Proxy(Kodi18Proxy):
    def __init__(self):
        Kodi18Proxy.__init__(self)

    class ListItem(Kodi18Proxy.ListItem):
        def __init__(self, label='', label2='', path='', offscreen=False):
            self.list_item = xbmcgui.ListItem(label=label, label2=label2, path=path, offscreen=offscreen)
            self.videoTag = self.list_item.getVideoInfoTag()

        def add_stream_info(self, type, info):
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

        def set_cast(self, cast):
            if len(cast) <= 0:
                return
            actors = []
            for c in cast:
                actors.append(xbmc.Actor(name=c['name'], role=c['role'], thumbnail=c['thumbnail']))
            self.videoTag.setCast(actors)

        def set_rating(self, type, rating, votes=0, default=True):
            self.videoTag.setRating(type=type, rating=float(rating), votes=votes, isdefault=default)

        def set_unique_ids(self, unique_ids):
            self.videoTag.setUniqueIDs(unique_ids.get_dict())

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
                self.videoTag.setPlaycount(0)
            elif flag == WatchedStatus.WATCHED:
                self.videoTag.setPlaycount(1)
            elif flag == WatchedStatus.PARTIAL and plugin_addon.getSetting('file_resume') == 'true':
                self.videoTag.setResumePoint(float(resume_time), float(total_time))
