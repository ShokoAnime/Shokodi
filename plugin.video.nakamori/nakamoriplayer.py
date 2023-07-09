# -*- coding: utf-8 -*-
import json
from threading import Thread

import xbmcgui

from lib.nakamori_utils.globalvars import *
from lib import error_handler as eh
from lib.error_handler import spam, log, ErrorPriority
from lib.nakamori_utils import script_utils
from lib.proxy.kodi_version_proxy import kodi_proxy

busy = xbmcgui.DialogProgress()


class PlaybackStatus(object):
    PLAYING = 'Playing'
    PAUSED = 'Paused'
    STOPPED = 'Stopped'
    ENDED = 'Ended'


def finished_episode(ep_id, file_id, current_time, total_time):
    _finished = False
    spam('finished_episode > ep_id = %s, file_id = %s, current_time = %s, total_time = %s' % (ep_id, file_id,
                                                                                              current_time, total_time))
    mark = float(plugin_addon.getSetting('watched_mark') or 75)
    if plugin_addon.getSetting('external_player').lower() == 'false':
        pass
    else:
        # mitigate the external player, skipping intro/outro/pv so we cut your setting in half
        mark /= 2
    mark /= 100
    spam('mark = %s * total (%s) = %s vs current = %s' % (mark, total_time, (total_time*mark), current_time))
    if (total_time * mark) <= current_time:
        _finished = True
        log('Video current_time (%s) has passed watch mark (%s). Marking is as watched!' % (current_time, (total_time*mark)))

    if _finished:
        if int(ep_id) != 0 and plugin_addon.getSetting('vote_always') == 'true':
            spam('vote_always, voting on episode')
            script_utils.vote_for_episode(ep_id)

        if ep_id != 0:
            from lib.shoko_models.v2 import Episode
            ep = Episode(ep_id, build_full_object=False)
            spam('mark as watched, episode')
            ep.set_watched_status(True)

            # vote on finished series
            if plugin_addon.getSetting('vote_on_series') == 'true':
                from lib.shoko_models.v2 import get_series_for_episode
                series = get_series_for_episode(ep_id)
                # voting should be only when you really watch full series
                spam('vote_on_series, mark: %s / %s' % (series.sizes.watched_episodes, series.sizes.total_episodes))
                if series.sizes.watched_episodes - series.sizes.total_episodes == 0:
                    script_utils.vote_for_series(series.id)

        elif file_id != 0:
            # file watched states
            pass

        # refresh only when we really did watch episode, this way we wait until all action after watching are executed
        script_utils.arbiter(10, 'Container.Refresh')


def play_video(file_id, ep_id=0, mark_as_watched=True, resume=False, episode=None):
    """
    Plays a file
    :param file_id: file ID. It is needed to look up the file
    :param ep_id: episode ID, not needed, but it fills in a lot of info
    :param mark_as_watched: should we mark it after playback
    :param resume: should we auto-resume
    :return: True if successfully playing
    """

    from lib.shoko_models.v2 import Episode, File, get_series_for_episode

    # check if we're already playing something
    try:
        player_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')
        active_players = json.loads(player_response)['results']

        while len(active_players) > 0:
            xbmc.sleep(500)
            player_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')
            active_players = json.loads(player_response)['results']
    except:
        pass

    # now continue
    file_url = ''

    if int(ep_id) != 0 or episode is not None:
        if episode is not None:
            ep = episode
            ep_id = episode.id
        else:
            ep = Episode(ep_id, build_full_object=True)
        series = get_series_for_episode(ep_id)
        ep.series_id = series.id
        ep.series_name = series.name
        item = ep.get_listitem()
        f = ep.get_file_with_id(file_id)
    else:
        f = None
        if episode is not None:
            f = episode.get_file_with_id(file_id)
            if f is None:
                f = episode.get_file()
        if f is None:
            f = File(file_id, build_full_object=True)
        item = f.get_listitem()

    if item is not None:
        if resume:
            item.resume()
        file_url = f.url_for_player if f is not None else None
        item.setPath(file_url)

    if file_url is not None:
        player = Player()
        player.feed(file_id, ep_id, f.duration, mark_as_watched)

        try:
            player.play(item=file_url, listitem=item)
        except:
            eh.exception(ErrorPriority.BLOCKING)

        player_loop(player)


def player_loop(player):
    try:
        monitor = xbmc.Monitor()

        while not player.isPlayingVideo():
            xbmc.sleep(100)

        spam('Player Loop: Started Playing - PlaybackState is: ', player.PlaybackStatus)

        while player.PlaybackStatus != PlaybackStatus.STOPPED and player.PlaybackStatus != PlaybackStatus.ENDED:
            xbmc.sleep(500)

        if player.PlaybackStatus == PlaybackStatus.STOPPED or player.PlaybackStatus == PlaybackStatus.ENDED:
            log('Playback Ended - Shutting Down: ', monitor.abortRequested())
        else:
            log('Playback Ended - Playback status was not "Stopped" or "Ended". It was ', player.PlaybackStatus)
    except:
        eh.exception(ErrorPriority.NORMAL)


# noinspection PyUnusedFunction
import xbmc
class Player(xbmc.Player):
    def __init__(self):
        spam('Player Initialized')
        xbmc.Player.__init__(self)
        self._s = None  # shoko thread
        self._details = None
        self.PlaybackStatus = PlaybackStatus.STOPPED
        self.file_id = 0
        self.ep_id = 0
        # we will store duration and time in kodi format here, so that calls to the player will match
        self.duration = 0
        self.time = 0
        self.scrobble = True
        self.is_external = False

        self.CanControl = True

    def reset(self):
        spam('Player reset')
        self.__init__()

    def feed(self, file_id, ep_id, duration, scrobble):
        spam('Player feed - file_id=%s ep_id=%s duration=%s scrobble=%s' %
             (file_id, ep_id, duration, scrobble))
        self.file_id = file_id
        self.ep_id = ep_id
        self.duration = kodi_proxy.duration_to_kodi(duration)
        self.scrobble = scrobble

    def start_loops(self):
        if self._s is None or not self._s.is_alive():
            self._s = Thread(target=self.tick_loop_shoko, args=())
            self._s.daemon = True
            self._s.start()

    def stop_loops(self):
        self.PlaybackStatus = PlaybackStatus.STOPPED
        while self._s is not None and self._s.is_alive():
            xbmc.sleep(100)

        self._s = None

    def onAVStarted(self):
        # Will be called when Kodi has a video or audiostream.
        spam('onAVStarted')

        # isExternalPlayer() ONLY works when isPlaying(), other than that it throw 0 always
        # setting it before results in false setting
        try:
            is_external = str(kodi_proxy.external_player(self)).lower()
            plugin_addon.setSetting(id='external_player', value=is_external)
            if kodi_proxy.external_player(self):
                log('Using External Player')
                self.is_external = True
        except:
            eh.exception(ErrorPriority.HIGH)

    def onAVChange(self):
        pass

    def onPlayBackStarted(self):
        spam('Playback Started')
        try:
            # wait until the player is init'd and playing
            self.set_duration()

            self.PlaybackStatus = PlaybackStatus.PLAYING
            self.start_loops()
            # we are making the player global, so if a stop is issued, then Playing will change
            while not self.isPlaying() and self.PlaybackStatus == PlaybackStatus.PLAYING:
                xbmc.sleep(100)
            if self.PlaybackStatus != PlaybackStatus.PLAYING:
                return
        except:
            eh.exception(ErrorPriority.HIGHEST)

    def onPlayBackResumed(self):
        spam('Playback Resumed')
        self.PlaybackStatus = PlaybackStatus.PLAYING
        try:
            self.start_loops()
        except:
            eh.exception(ErrorPriority.HIGH)

    def onPlayBackStopped(self):
        spam('Playback Stopped')
        try:
            self.stop_loops()
            self.handle_finished_episode()
        except:
            eh.exception(ErrorPriority.HIGH)
        self.PlaybackStatus = PlaybackStatus.STOPPED

    def onPlayBackEnded(self):
        spam('Playback Ended')
        try:
            self.stop_loops()
            self.handle_finished_episode()
        except:
            eh.exception(ErrorPriority.HIGH)
        self.PlaybackStatus = PlaybackStatus.ENDED

    def onPlayBackPaused(self):
        spam('Playback Paused')
        self.PlaybackStatus = PlaybackStatus.PAUSED
        self.scrobble_time()
        self.stop_loops()

    def onPlayBackSeek(self, time_to_seek, seek_offset):
        log('Playback Paused - time_to_seek=%s seek_offset=%s' % (time_to_seek, seek_offset))
        self.time = self.getTime()
        self.scrobble_time()

    def set_duration(self):
        if self.duration != 0:
            return
        duration = int(self.getTotalTime())
        self.duration = duration

    def scrobble_time(self):
        if not self.scrobble:
            return
        try:
            if self.time > 10:
                from lib.shoko_models.v2 import File
                f = File(self.file_id)
                f.set_resume_time(kodi_proxy.duration_from_kodi(self.time))
        except:
            eh.exception(ErrorPriority.HIGH)

    def wait_for_playback(self):
        if self.isPlayingVideo() and self.PlaybackStatus == PlaybackStatus.PLAYING:
            return True

        # try for 10s to start playing
        count = 0
        while count < 20 and not (self.isPlayingVideo() and self.PlaybackStatus == PlaybackStatus.PLAYING):
            count += 1
            xbmc.sleep(500)

        return self.isPlayingVideo() and self.PlaybackStatus == PlaybackStatus.PLAYING

    def tick_loop_shoko(self):
        try:
            if not self.scrobble:
                log('Scrobble Thread Exiting: Scrobbling not enabled')
                return

            if plugin_addon.getSetting('file_resume').lower() == 'false':
                log('Scrobble Thread Exiting: Resume not enabled')
                return

            if self.is_external:
                log('Scrobble Thread Exiting: Not supported in external players')
                return

            if not self.wait_for_playback():
                log('Scrobble Thread Exiting: Player did not start playing in an acceptable time')
                return

            while self.isPlayingVideo() and self.PlaybackStatus == PlaybackStatus.PLAYING:
                try:
                    self.set_duration()
                    self.time = self.getTime()

                    if self.time <= 10:
                        xbmc.sleep(2500)
                        continue

                    self.scrobble_time()
                    xbmc.sleep(2500)
                except:
                    pass  # while buffering

            log('Scrobble Thread Exiting: Stopped Playing')
        except:
            eh.exception(ErrorPriority.NORMAL)

    def handle_finished_episode(self):
        finished_episode(self.ep_id, self.file_id, self.time, self.duration)
