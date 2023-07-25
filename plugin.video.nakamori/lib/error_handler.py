# -*- coding: utf-8 -*-
import inspect
import os
import sys
import traceback
from collections import defaultdict, Counter

import xbmc
import xbmcgui
from lib import class_dump
from lib.nakamori_utils.globalvars import plugin_addon, plugin_version, translatePath


try:
    addon_path = 'special://home/addons'
    addon_path = translatePath(addon_path).replace('\\', '/')
except (ImportError, NameError):
    addon_path = os.path.expanduser('~/Documents/GitHub/Nakamori').replace('\\', '/')
    from lib import kodi_dummy as xbmc


# The plan is:
# gather all errors/exceptions, regardless of whether they are painless
# sort and group them
# BLOCKING errors will immediately return and break
# otherwise, log only HIGH and above priority errors
# log the count and place(s) of occurrence
# Show a dialog OK message that there was an error if it was HIGHEST or greater
# Show a notification if it was HIGH
# log counts of normal errors if they happen a lot, like more than 5 times
# We will normally not even log LOW priority errors,
# but we may enable it (and logging all errors) in the settings
# Errors will start being collected at the start of the plugin cycle, and will only show messages when done
# Especially suppress errors during playback unless it is BLOCKING


class ErrorPriority:
    """
    | **BLOCKING**: Something that prevents continuing.
    | **HIGHEST**: An entire item failed to parse or something. May impact the user greatly. We show a dialog.
    | **HIGH**: Some data failed to parse, or a command couldn't succeed. May impact the user. Notification.
    | **NORMAL**: Something that we handle separately. It shows no message, but logs it fully
    | **LOW**: couldn't keep up scrobbling or something that shouldn't happen often, but isn't really a problem most of the time. Log it if there's more than 5.
    | **LOWEST**: Basically negligible. They could happen all day, and the user wouldn't even care.
    An example of LOW might be needing to internally retry selecting the next unwatched episode, as it wasn't ready yet.
    We don't even log them unless spam log is on.
    """

    class ErrorPriority:
        def __init__(self, value, name):
            self.value = value
            self.name = name

        def __int__(self):
            return self.value

        def __str__(self):
            return self.name

    LOWEST = ErrorPriority(0, 'LOWEST')
    LOW = ErrorPriority(1, 'LOW')
    NORMAL = ErrorPriority(2, 'NORMAL')
    HIGH = ErrorPriority(3, 'HIGH')
    HIGHEST = ErrorPriority(4, 'HIGHEST')
    BLOCKING = ErrorPriority(5, 'BLOCKING')


class NakamoriError(object):
    """
    The error object has the point of carrying the traceback and exception info.
    It may also carry some extra data or less data, if the error is raised by us with a specific message
    """
    def __init__(self, message='Something Happened :(', ex=Exception.__name__, trace='error_handler.py#L61'):
        # the message, either from the exception or us
        self.exc_message = message
        if not isinstance(ex, str):
            ex = ex.__name__
        # the Exception type, in str form
        self.exc_type = ex
        # (str, int) that carries the file and line number, relative to the addon directory
        self.exc_trace = trace
        # this is for spam log or BLOCKING errors. It contains the full trace info, in list form at 1 line each
        self.exc_full_trace = []

    def __eq__(self, o):
        if not isinstance(o, NakamoriError):
            return False
        return self.exc_type == o.exc_type and self.exc_message == o.exc_message and self.exc_trace == o.exc_trace

    def __hash__(self):
        return hash((self.exc_type, self.exc_message, self.exc_trace))

    def __lt__(self, other):
        if not isinstance(other, NakamoriError):
            return True
        return (self.exc_type, self.exc_message, self.exc_trace) < (other.exc_type, other.exc_message, other.exc_trace)


# I WANT LINQ!!!!!!
# a dictionary of ErrorPriority to list of errors
__exceptions = defaultdict(list)

file_exclusions = {'error_handler', 'routing', '__init__'}


def try_function(error_priority, message='', except_func=None, *exc_args, **exc_kwargs):
    def try_inner1(func):
        def try_inner2(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                exception(error_priority, message)
                if except_func is not None:
                    except_func(*exc_args, **exc_kwargs)
                if error_priority == ErrorPriority.BLOCKING:
                    show_messages()
                    # sys.exit is called if BLOCKING errors exist in the above
                return None
        return try_inner2
    return try_inner1


def kodi_log(text):
    xbmc.log(text, xbmc.LOGINFO)


def kodi_error(text):
    xbmc.log(text, xbmc.LOGERROR)


# noinspection PyProtectedMember
def get_simple_trace(fullpath=False):
    # this gets the frame that is not in this file
    filepath, line_number, clsname, class_name, lines, index, path = '', 0, '', '', [], 0, ''
    for frame_index in range(0, 12):
        try:
            f = sys._getframe(frame_index)
            filepath, line_number, clsname, lines, index = inspect.getframeinfo(f)
            try:
                class_name = f.f_locals['self'].__class__.__name__
            except:
                pass

            frame_path = os.path.split(filepath)[-1]
            frame_path = os.path.splitext(frame_path)[0]

            if not fullpath:
                path = frame_path
            else:
                path = filepath.replace('\\', '/').replace(addon_path, '.')

            if frame_path not in file_exclusions:
                break
        except:
            break

    if clsname == '<module>':
        filename = path + '#L' + str(line_number)
    elif class_name != '':
        filename = path + '::' + class_name + '::' + clsname + '#L' + str(line_number)
    else:
        filename = path + '::' + clsname + '#L' + str(line_number)

    return filename


def __get_caller_prefix():
    return 'Nakamori|' + get_simple_trace() + ' -> '


def __get_basic_prefix():
    return 'Nakamori|Logger -> '


def spam(*args):
    if plugin_addon.getSetting('spamLog') == 'true':
        log(*args)


def log(*args):
    """
    Print a message on the NOTICE stream, with a simple traceback.
    This is for readable messages that are expected.
    If you want to log a full traceback use exception()
    :param args: some objects to log
    :return:
    """
    from lib.proxy.python_version_proxy import python_proxy as pp
    try:
        text = class_dump.dump_to_text(*args)
    except:
        text = ''
        exception(ErrorPriority.NORMAL, 'Unable to dump args for error_handler.log')

    if text == '':
        return
    kodi_log(__get_caller_prefix() + pp.decode(text))


def error(*args):
    """
    Print a message on the ERROR stream, with a simple traceback.
    This is for readable messages that are expected, such as connection errors.
    If you want to log a full traceback use exception()
    :param args: some objects to log
    :return:
    """
    from lib.proxy.python_version_proxy import python_proxy as pp
    text = class_dump.dump_to_text(*args)
    if text == '':
        return
    kodi_error(__get_caller_prefix() + pp.decode(text))


def exception(priority, *args):
    exc_type, exc_obj, exc_tb = None, None, None
    try:
        exc_type, exc_obj, exc_tb = sys.exc_info()
    except:
        # We don't actually have an Exception
        pass
    text = class_dump.dump_to_text(*args)
    exception_internal(exc_type, exc_obj, exc_tb, priority, text)


def exception_internal(exc_type, exc_obj, exc_tb, priority, message=''):
    """
    The priority determines how the system will handle or display the error. The message is self-explanatory.
    sys.exc_info() will give the required information for the first arguments. Otherwise, just pass None to them.
    :param exc_type:
    :param exc_obj:
    :type exc_obj: Exception
    :param exc_tb:
    :param priority: The priority of the Error
    :type priority: ErrorPriority
    :param message: a custom message to give the user. If left blank, it will use the exception's
    :return:
    """
    msg = message
    # apparently sometimes they give us exc_type as a str instead of a type
    if exc_type is None:
        exc_type = 'Exception'
    if not isinstance(exc_type, str):
        exc_type = exc_type.__name__

    place = get_simple_trace(fullpath=True)

    if exc_obj is not None and exc_tb is not None:
        if msg == '':
            msg = str(exc_obj)
        ex = NakamoriError(msg, exc_type, place)
        if priority == ErrorPriority.BLOCKING or plugin_addon.getSetting('spamLog') == 'true':
            for line in traceback.format_exc().replace('\r', '\n').split('\n'):
                # skip empty lines
                if len(line) == 0:
                    continue
                # skip the try_function wrapper
                if ' in try_inner2' in line or 'return func(*args, **kwargs)' in line or 'error_handler' in line:
                    continue

                tr = line.replace('\\', '/').replace(addon_path, '.')
                ex.exc_full_trace.append(tr)
    else:
        ex = NakamoriError(msg, exc_type, place)
    # Learning opportunity! If you don't want it to interrupt you with errors, then change the logic in show_...
    # That way, you will still get logs of the errors, but no interruptions!
    # With the previous logic, you are basically saying `if False: else xbmc.log()`
    __exceptions[priority].append(ex)


def show_messages():
    # finalize the defaultdict so that it won't create new keys anymore
    __exceptions.default_factory = None
    if len(__exceptions) == 0:
        return
    if ErrorPriority.BLOCKING in __exceptions:
        exes = __exceptions[ErrorPriority.BLOCKING]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_dialog_for_exception(exes[0])
        sys.exit()
    if ErrorPriority.HIGHEST in __exceptions:
        exes = __exceptions[ErrorPriority.HIGHEST]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_dialog_for_exception(exes[0])
    if ErrorPriority.HIGH in __exceptions:
        exes = __exceptions[ErrorPriority.HIGH]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_notification_for_exception(exes[0])
    if ErrorPriority.NORMAL in __exceptions:
        exes = __exceptions[ErrorPriority.NORMAL]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
    if ErrorPriority.LOW in __exceptions:
        exes = __exceptions[ErrorPriority.LOW]
        exes = Counter(exes).items()
        exes = sorted(exes)
        # log all if we are spamming
        if plugin_addon.getSetting('spamLog') != 'true':
            exes = [x for x in exes if x[1] > 5]
        print_exceptions(exes)
    if plugin_addon.getSetting('spamLog') == 'true' and ErrorPriority.LOWEST in __exceptions:
        exes = __exceptions[ErrorPriority.LOWEST]
        exes = Counter(exes).items()
        exes = sorted(exes)
        # log only if we are spamming
        if plugin_addon.getSetting('spamLog') != 'true':
            exes = [x for x in exes if x[1] > 5]
            print_exceptions(exes)


def print_exceptions(exes):
    from lib.proxy.python_version_proxy import python_proxy as pp
    if exes is None or len(exes) == 0:
        return

    plural = True if len(exes) > 1 else False
    pluralized_msg = 'were errors' if plural else 'was an error'
    msg = 'There ' + pluralized_msg + ' while executing Nakamori.'
    kodi_error(__get_basic_prefix() + msg)

    msg = 'Nakamori Version ' + str(plugin_version)
    kodi_error(__get_basic_prefix() + msg)

    url = sys.argv[0]
    if len(sys.argv) > 2 and sys.argv[2] != '':
        url += sys.argv[2]
    msg = 'The url accessed was ' + pp.unquote(url)
    kodi_error(__get_basic_prefix() + msg)

    for ex in exes:
        key, value = ex  # type: NakamoriError, int
        msg = key.exc_message + ' -- Exception: ' + key.exc_type + ' at ' + key.exc_trace
        kodi_error(__get_basic_prefix() + msg)
        if len(key.exc_full_trace) > 0:
            for line in key.exc_full_trace:
                kodi_error(__get_basic_prefix() + line)

        if value > 1:
            msg = 'This error occurred ' + str(value) + ' times.'
            kodi_error(__get_basic_prefix() + msg)


def show_dialog_for_exception(ex):
    """
    Show an OK dialog to say that errors occurred
    :param ex: a tuple of the error and the number of times it occurred
    :type ex: (NakamoriError, int)
    :return:
    """

    msg = ex[0].exc_message
    if msg == '':
        msg = ex[0].exc_type
    msg += '\n  at ' + ex[0].exc_trace + '\nThis occurred ' + \
        str(ex[1]) + ' times.'
    xbmcgui.Dialog().ok('Nakamori: An Error Occurred', msg)


def show_notification_for_exception(ex):
    """
    Show a notification to say that errors occurred
    :param ex: a tuple of the error and the number of times it occurred
    :type ex: (NakamoriError, int)
    :return:
    """
    msg = ex[0].exc_message + '\nThis occurred ' + str(ex[1]) + ' times.'
    xbmc.executebuiltin('Notification(Nakamori: An Error Occurred, ' + msg + ', 2000, ' +
                        plugin_addon.getAddonInfo('icon') + ')')
