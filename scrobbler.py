# -*- coding: utf-8 -*-
#

import xbmc
import time
import logging
from resources.lib import utilities
from resources.lib import kodiUtilities
import math
from resources.lib.rating import ratingCheck

logger = logging.getLogger(__name__)


class Scrobbler:
    isPlaying = False
    isPaused = False
    stopScrobbler = False
    videoDuration = 1
    watchedTime = 0
    pausedAt = 0
    curVideo = None
    curVideoInfo = None
    playlistIndex = 0
    traktShowSummary = None
    videosToRate = []

    def _currentEpisode(self, watchedPercent, episodeCount):
        split = (100 / episodeCount)
        for i in range(episodeCount - 1, 0, -1):
            if watchedPercent >= (i * split):
                return i
        return 0

    def transitionCheck(self, isSeek=False):
        if not xbmc.Player().isPlayingVideo():
            return

        if self.isPlaying:
            t = xbmc.Player().getTime()
            l = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
            if self.playlistIndex == l:
                self.watchedTime = t
            else:
                logger.debug(
                    "Current playlist item changed! Not updating time! (%d -> %d)" % (self.playlistIndex, l))

            # do transition check every minute
            if isSeek:
                self.__scrobble('start')

    def playbackStarted(self, data):
        logger.debug("playbackStarted(data: %s)" % data)
        if not data:
            return
        self.curVideo = data
        self.curVideoInfo = None
        self.videosToRate = []

        if not kodiUtilities.getSettingAsBool('scrobble_fallback') and 'id' not in self.curVideo and 'video_ids' not in self.curVideo:
            logger.debug('Aborting scrobble to avoid fallback: %s' %
                         (self.curVideo))
            return

        if 'type' in self.curVideo:
            logger.debug("Watching: %s" % self.curVideo['type'])
            if not xbmc.Player().isPlayingVideo():
                logger.debug("Suddenly stopped watching item")
                return
            # Wait for possible silent seek (caused by resuming)
            xbmc.sleep(1000)
            try:
                self.watchedTime = xbmc.Player().getTime()
                self.videoDuration = 0
                self.videoDuration = xbmc.Player().getTotalTime()
            except Exception as e:
                logger.debug("Suddenly stopped watching item: %s" % e.message)
                self.curVideo = None
                return

            if self.videoDuration == 0:
                if utilities.isMovie(self.curVideo['type']):
                    self.videoDuration = 90
                elif utilities.isEpisode(self.curVideo['type']):
                    self.videoDuration = 30
                else:
                    self.videoDuration = 1

            self.playlistIndex = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()

            if utilities.isMovie(self.curVideo['type']):
                if 'id' in self.curVideo:
                    self.curVideoInfo = kodiUtilities.kodiRpcToTraktMediaObject('movie', kodiUtilities.getMovieDetailsFromKodi(
                        self.curVideo['id'], ['uniqueid', 'imdbnumber', 'title', 'year', 'file', 'lastplayed', 'playcount']))
                elif 'video_ids' in self.curVideo:
                    self.curVideoInfo = {'ids': self.curVideo['video_ids']}
                elif 'title' in self.curVideo and 'year' in self.curVideo:
                    self.curVideoInfo = {
                        'title': self.curVideo['title'], 'year': self.curVideo['year']}
                else:
                    logger.debug("Couldn't set curVideoInfo for movie type")
                logger.debug("Movie type, curVideoInfo: %s" %
                             self.curVideoInfo)

            elif utilities.isEpisode(self.curVideo['type']):
                if 'id' in self.curVideo:
                    episodeDetailsKodi = kodiUtilities.getEpisodeDetailsFromKodi(self.curVideo['id'], [
                                                                                 'showtitle', 'season', 'episode', 'tvshowid', 'uniqueid', 'file', 'playcount'])
                    title, year = utilities.regex_year(
                        episodeDetailsKodi['showtitle'])
                    if not year:
                        self.traktShowSummary = {
                            'title': episodeDetailsKodi['showtitle'], 'year': episodeDetailsKodi['year']}
                    else:
                        self.traktShowSummary = {'title': title, 'year': year}
                    if 'show_ids' in episodeDetailsKodi:
                        self.traktShowSummary['ids'] = episodeDetailsKodi['show_ids']
                    self.curVideoInfo = kodiUtilities.kodiRpcToTraktMediaObject(
                        'episode', episodeDetailsKodi)
                    if not self.curVideoInfo:  # getEpisodeDetailsFromKodi was empty
                        logger.debug(
                            "Episode details from Kodi was empty, ID (%d) seems invalid, aborting further scrobbling of this episode." % self.curVideo['id'])
                        self.curVideo = None
                        self.isPlaying = False
                        self.watchedTime = 0
                        return
                elif 'video_ids' in self.curVideo and 'season' in self.curVideo and 'episode' in self.curVideo:
                    self.curVideoInfo = {
                        'season': self.curVideo['season'], 'number': self.curVideo['episode']}
                    self.traktShowSummary = {'ids': self.curVideo['video_ids']}
                elif 'title' in self.curVideo and 'season' in self.curVideo and 'episode' in self.curVideo:
                    self.curVideoInfo = {'title': self.curVideo['title'], 'season': self.curVideo['season'],
                                         'number': self.curVideo['episode']}

                    title, year = utilities.regex_year(
                        self.curVideo['showtitle'])
                    if not year:
                        self.traktShowSummary = {
                            'title': self.curVideo['showtitle']}
                    else:
                        self.traktShowSummary = {'title': title, 'year': year}

                    if 'year' in self.curVideo:
                        self.traktShowSummary['year'] = self.curVideo['year']
                else:
                    logger.debug(
                        "Couldn't set curVideoInfo/traktShowSummary for episode type")

                logger.debug("Episode type, curVideoInfo: %s" %
                             self.curVideoInfo)
                logger.debug("Episode type, traktShowSummary: %s" %
                             self.traktShowSummary)

            self.isPlaying = True
            self.isPaused = False

            result = {}
            if kodiUtilities.getSettingAsBool('scrobble_movie') or kodiUtilities.getSettingAsBool('scrobble_episode'):
                result = self.__scrobble('start')

            if 'id' in self.curVideo:
                if utilities.isMovie(self.curVideo['type']):
                    result['movie']['movieid'] = self.curVideo['id']
                elif utilities.isEpisode(self.curVideo['type']):
                    result['episode']['episodeid'] = self.curVideo['id']

    def playbackResumed(self):
        if not self.isPlaying:
            return

        logger.debug("playbackResumed()")
        if self.isPaused:
            p = time.time() - self.pausedAt
            logger.debug("Resumed after: %s" % str(p))
            self.pausedAt = 0
            self.isPaused = False
            self.__scrobble('start')

    def playbackPaused(self):
        if not self.isPlaying:
            return

        logger.debug("playbackPaused()")
        logger.debug("Paused after: %s" % str(self.watchedTime))
        self.isPaused = True
        self.pausedAt = time.time()
        self.__scrobble('pause')

    def playbackSeek(self):
        if not self.isPlaying:
            return

        logger.debug("playbackSeek()")
        self.transitionCheck(isSeek=True)

    def playbackEnded(self):
        self.videosToRate.append(self.curVideoInfo)
        if not self.isPlaying:
            return

        logger.debug("playbackEnded()")
        if not self.videosToRate:
            logger.debug("Warning: Playback ended but video forgotten.")
            return
        self.isPlaying = False
        self.stopScrobbler = False
        if self.watchedTime != 0:
            if 'type' in self.curVideo:
                self.__scrobble('stop')
                ratingCheck(
                    self.curVideo['type'], self.videosToRate, self.watchedTime, self.videoDuration)
            self.watchedTime = 0
        self.videosToRate = []
        self.curVideoInfo = None
        self.curVideo = None
        self.playlistIndex = 0

    def __calculateWatchedPercent(self):
        # we need to floor this, so this calculation yields the same result as the playback progress calculation
        floored = math.floor(self.videoDuration)
        if floored != 0:
            return (self.watchedTime / floored) * 100
        else:
            return 0

    def __scrobble(self, status):
        if not self.curVideoInfo:
            return

        logger.debug("scrobble()")
        scrobbleMovieOption = kodiUtilities.getSettingAsBool('scrobble_movie')
        scrobbleEpisodeOption = kodiUtilities.getSettingAsBool(
            'scrobble_episode')

        watchedPercent = self.__calculateWatchedPercent()
        if utilities.isMovie(self.curVideo['type']) and scrobbleMovieOption:
            response = self.traktapi.scrobbleMovie(
                self.curVideoInfo, watchedPercent, status)
            if response is not None:
                self.__scrobbleNotification(response)
                logger.debug("Scrobble response: %s" % str(response))
                return response
            else:
                logger.debug("Failed to scrobble movie: %s | %s | %s" %
                             (self.curVideoInfo, watchedPercent, status))

        elif utilities.isEpisode(self.curVideo['type']) and scrobbleEpisodeOption:
            if self.isMultiPartEpisode:
                logger.debug("Multi-part episode, scrobbling part %d of %d." %
                             (self.curMPEpisode + 1, self.curVideo['multi_episode_count']))
                adjustedDuration = int(
                    self.videoDuration / self.curVideo['multi_episode_count'])
                watchedPercent = (
                    (self.watchedTime - (adjustedDuration * self.curMPEpisode)) / adjustedDuration) * 100

            logger.debug("scrobble sending show object: %s" %
                         str(self.traktShowSummary))
            logger.debug("scrobble sending episode object: %s" %
                         str(self.curVideoInfo))
            response = self.traktapi.scrobbleEpisode(
                self.traktShowSummary, self.curVideoInfo, watchedPercent, status)

            if (kodiUtilities.getSettingAsBool('scrobble_secondary_title')):
                logger.debug(
                    '[traktPlayer] Setting is enabled to try secondary show title, if necessary.')
                # If there is an empty response, the reason might be that the title we have isn't the actual show title,
                # but rather an alternative title. To handle this case, call the Trakt search function.
                if response is None:
                    logger.debug("Searching for show title: %s" %
                                 self.traktShowSummary['title'])
                    # This text query API is basically the same as searching on the website. Works with alternative
                    # titles, unlike the scrobble function.
                    newResp = self.traktapi.getTextQuery(
                        self.traktShowSummary['title'], "show", None)
                    if not newResp:
                        logger.debug(
                            "Empty Response from getTextQuery, giving up")
                    else:
                        logger.debug(
                            "Got Response from getTextQuery: %s" % str(newResp))
                        # We got something back. Have to assume the first show found is the right one; if there's more than
                        # one, there's no way to know which to use. Pull the primary title from the response (and the year,
                        # just because it's there).
                        showObj = {
                            'title': newResp[0].title, 'year': newResp[0].year}
                        logger.debug(
                            "scrobble sending getTextQuery first show object: %s" % str(showObj))
                        # Now we can attempt the scrobble again, using the primary title this time.
                        response = self.traktapi.scrobbleEpisode(
                            showObj, self.curVideoInfo, watchedPercent, status)

            if response is not None:
                # Don't scrobble incorrect episode, episode numbers can differ from database. ie Aired vs. DVD order. Use fuzzy logic to match episode title.
                if self.isPVR and not utilities._fuzzyMatch(self.curVideoInfo['title'], response['episode']['title'], 50.0):
                    logger.debug("scrobble sending incorrect scrobbleEpisode stopping: %sx%s - %s != %s" % (
                        self.curVideoInfo['season'], self.curVideoInfo['number'], self.curVideoInfo['title'], response['episode']['title']))
                    self.stopScrobbler = True

                self.__scrobbleNotification(response)
                logger.debug("Scrobble response: %s" % str(response))
                return response
            else:
                logger.debug("Failed to scrobble episode: %s | %s | %s | %s" % (self.traktShowSummary,
                                                                                self.curVideoInfo, watchedPercent,
                                                                                status))

    def __scrobbleNotification(self, info):
        if not self.curVideoInfo:
            return

        if kodiUtilities.getSettingAsBool("scrobble_notification"):
            s = utilities.getFormattedItemName(
                self.curVideo['type'], info[self.curVideo['type']])
            kodiUtilities.notification(kodiUtilities.getString(32015), s)
