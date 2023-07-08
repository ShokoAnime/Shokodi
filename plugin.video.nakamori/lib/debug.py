# -*- coding: utf-8 -*-
import cProfile
import pstats
import sys
from lib.nakamori_utils.globalvars import *
from lib import error_handler as eh
from lib.error_handler import ErrorPriority
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

has_line_profiler = False
try:
    # noinspection PyUnresolvedReferences
    import line_profiler as line_profiler
    has_line_profiler = True
except ImportError:
    pass


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
            profile.enable(builtins=False)
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            stream = StringIO()
            sort_by = u'cumulative'
            ps = pstats.Stats(profile, stream=stream).sort_stats(sort_by)
            ps.print_stats(20)
            xbmc.log(u'Profiled Function: ' + func.__name__ + u'\n' + stream.getvalue(), xbmc.LOGWARNING)
    return profiled_func


def debug_init():
    """
    start debugger if it's enabled
    also dump argv if spamLog
    :return:
    """
    if plugin_addon.getSetting('remote_debug') == 'true':
        # try pycharm first
        try:
            import pydevd
            # try to connect multiple times...in case we forgot to start it
            # TODO Show a message to the user that we are waiting on the debugger
            connected = False
            tries = 0
            while not connected and tries < 60:
                try:
                    pydevd.settrace(host=plugin_addon.getSetting('remote_ip'), stdoutToServer=True, stderrToServer=True,
                                    port=5678, suspend=False)
                    eh.spam('Connected to debugger')
                    connected = True
                except:
                    tries += 1
                    # we keep this message the same, as kodi will merge them into Previous line repeats...
                    eh.spam('Failed to connect to debugger')
                    xbmc.sleep(1000)
        except (ImportError, NameError):
            eh.log('unable to import pycharm debugger, falling back on the web-pdb')
            try:
                import web_pdb
                web_pdb.set_trace()
            except:
                eh.exception(ErrorPriority.NORMAL, 'Unable to start debugger, disabling it')
                plugin_addon.setSetting('remote_debug', 'false')
        except:
            eh.exception(ErrorPriority.HIGHEST, 'Unable to start debugger')

    eh.spam('argv:', sys.argv)
