# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import inspect
import re
import sys

try:
    from urlparse import urlsplit, parse_qs
except ImportError:
    from urllib.parse import urlsplit, parse_qs
try:
    from urllib import urlencode, quote_plus, unquote_plus
except ImportError:
    from urllib.parse import urlencode, quote_plus, unquote_plus


def print_this(msg):
    try:
        print(msg)
    except:
        pass

try:
    import xbmc
    import xbmcaddon
    _addon_id = xbmcaddon.Addon().getAddonInfo('id')

    def log(msg):
        msg = "[%s][routing] %s" % (_addon_id, msg)
        xbmc.log(msg, level=xbmc.LOGDEBUG)
except ImportError:
    def log(msg):
        print_this(msg)


class RoutingError(Exception):
    pass


class Addon(object):
    """
    The base class for routing.Plugin, Script, and any others that may be added
    :ivar args: The parsed query string.
    :type args: dict of byte strings

    :ivar base_url: the base_url of the addon, ex. plugin://plugin.video.something_plugin
    :type base_url: str

    :ivar convert_args: Convert arguments to basic types
    :type convert_args: bool
    """

    def __init__(self, base_url=None, convert_args=False, instance=None):
        self._rules = {}  # function to list of rules
        if sys.argv:
            self.path = urlsplit(sys.argv[0]).path or '/'
        else:
            self.path = '/'
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            self.handle = int(sys.argv[1])
        else:
            self.handle = -1
        self.args = {}
        self.convert_args = convert_args

        self.base_url = base_url
        if self.base_url is None:
            self.base_url = "plugin://" + _addon_id
        elif not self.base_url.startswith('plugin://'):
            self.base_url = 'plugin://' + self.base_url.rstrip('/')

        self.instance = instance

    def route_for(self, path):
        """
        Returns the view function for path.

        :type path: byte string.
        """
        if path.startswith(self.base_url):
            path = path.split(self.base_url, 1)[1]

        # only list convert once
        list_rules = list(self._rules.items())

        # first, search for exact matches
        for view_fun, rules in iter(list_rules):
            for rule in rules:
                if rule.exact_match(path):
                    return view_fun

        # then, search for regex matches
        for view_fun, rules in iter(list_rules):
            for rule in rules:
                if rule.match(path) is not None:
                    return view_fun
        return None

    def url_for(self, func, *args, **kwargs):
        """
        Construct and returns an URL for view function with give arguments.
        """
        for key in self._rules.keys():
            if func.__name__ != key.__name__:
                continue

            for rule in self._rules[key]:  # type: UrlRule
                path = rule.make_path(func, *args, **kwargs)
                if path is not None:
                    return self.url_for_path(path)
        raise RoutingError("No known paths to '{0}' with args {1} and "
                           "kwargs {2}".format(func.__name__, args, kwargs))

    def url_for_path(self, path):
        """
        Returns the complete URL for a path.
        """
        path = path if path.startswith('/') else '/' + path
        return self.base_url + path

    def route(self, pattern):
        """ Register a route. """
        def decorator(func):
            self.add_route(func, pattern)
            return func
        return decorator

    def add_route(self, func, pattern):
        """ Register a route. """
        rule = UrlRule(pattern)
        if func not in self._rules:
            self._rules[func] = []
        self._rules[func].append(rule)

    def run(self, argv=None):
        pass

    def redirect(self, path):
        self._dispatch(path)

    def _dispatch(self, path):
        list_rules = list(self._rules.items())
        for view_func, rules in iter(list_rules):
            for rule in rules:
                if not rule.exact_match(path):
                    continue
                log("Dispatching to '%s', exact match" % view_func.__name__)
                if self.instance is not None:
                    inst_func = self.instance.__getattribute__(view_func.__name__)
                    inst_func()
                else:
                    view_func()
                return

        # then, search for regex matches
        for view_func, rules in iter(list_rules):
            for rule in rules:
                kwargs = rule.match(path)
                if kwargs is None:
                    continue
                if self.convert_args:
                    kwargs = dict((k, try_convert(v)) for k, v in list(kwargs.items()))
                log("Dispatching to '%s', args: %s" % (view_func.__name__, kwargs))
                if self.instance is not None:
                    inst_func = self.instance.__getattribute__(view_func.__name__)
                    inst_func(**kwargs)
                else:
                    view_func(**kwargs)
                return
        raise RoutingError('No route to path "%s"' % path)

    def get_routes(self):
        # type: (Addon) -> list[UrlRule]
        return self._rules.values()


class Plugin(Addon):
    """
    A routing handler bound to a kodi plugin
    :ivar handle: The plugin handle from kodi
    :type handle: int
    """

    def __init__(self, base_url=None, convert_args=False, instance=None):
        self.base_url = base_url
        Addon.__init__(self, self.base_url, convert_args, instance)
        if len(sys.argv) < 2:
            # we are probably not dealing with a plugin, or it was called incorrectly from an addon
            raise TypeError('There was no handle provided. This needs to be called from a Kodi Plugin.')
        self.handle = int(sys.argv[1]) if sys.argv[1].isdigit() else -1

    def run(self, argv=None):
        if argv is None:
            argv = sys.argv
        self.path = urlsplit(argv[0]).path
        self.path = self.path.rstrip('/')
        if len(argv) > 2:
            self.args = parse_qs(argv[2].lstrip('?'))
        self._dispatch(self.path)


class Script(Addon):
    """
    A routing handler bound to a kodi script
    """

    def __init__(self, base_url=None, convert_args=False, instance=None):
        self.base_url = base_url
        if self.base_url is None:
            self.base_url = "script://" + _addon_id
        elif not self.base_url.startswith('script://'):
            self.base_url = 'script://' + self.base_url.rstrip('/')

        Addon.__init__(self, base_url, convert_args, instance=instance)

    def run(self, argv=None):
        if argv is None:
            argv = sys.argv
        if len(argv) > 1:
            # parse query
            self.args = parse_qs(argv[1].lstrip('?'))
            # handle ['script.module.fun', '/do/something']
            path = urlsplit(argv[1]).path or '/'
        else:
            # handle ['script.module.fun/do/something']
            temp = urlsplit(argv[0]).path
            path = temp if temp != self.base_url else '/'
        self.path = path.rstrip('/')
        self._dispatch(path)

    def url_for(self, func, *args, **kwargs):
        """
        Construct and returns an URL for view function with give arguments.
        """
        for key in self._rules.keys():
            if func.__name__ != key.__name__:
                continue

            for rule in self._rules[key]:  # type: UrlRule
                path = rule.make_path(func, *args, **kwargs)
                if path is not None:
                    path = path if path.startswith('/') else '/' + path
                    return 'RunScript(%s,%s)' % (_addon_id, path)
        raise RoutingError("No known paths to '{0}' with args {1} and "
                           "kwargs {2}".format(func.__name__, args, kwargs))


class UrlRule:
    def __init__(self, pattern):
        arg_regex = re.compile('<([A-z_][A-z0-9_]*)>')
        self._has_args = bool(arg_regex.search(pattern))

        kw_pattern = r'<(?:[A-Za-z]+:)?([A-Za-z_][A-Za-z0-9_]*)>'
        self._pattern = re.sub(kw_pattern, '{\\1}', pattern)
        self._keywords = re.findall(kw_pattern, pattern)

        p = re.sub('<([A-Za-z_][A-Za-z0-9_]*)>', '<string:\\1>', pattern)
        p = re.sub('<string:([A-Za-z_][A-Za-z0-9_]*)>', '(?P<\\1>[^/]+?)', p)
        p = re.sub('<path:([A-Za-z_][A-Za-z0-9_]*)>', '(?P<\\1>.*)', p)
        self._regex = re.compile('^%s$' % p.rstrip('/'))

    def match(self, path):
        """
        Check if path matches this rule. Returns a dictionary of the extracted
        arguments if match, otherwise None.
        """
        # match = self._regex.search(urlsplit(path).path)
        match = self._regex.search(path.rstrip('/'))
        return dict((k, unquote_plus(v)) for k, v in match.groupdict().items()) if match else None

    def exact_match(self, path):
        return not self._has_args and self._pattern.rstrip('/') == path.rstrip('/')

    def make_path(self, func, *args, **kwargs):
        """Construct a path from arguments."""
        if args and kwargs:
            return None  # can't use both args and kwargs
        if args:
            # Replace the named groups %s and format
            try:
                args = tuple(quote_plus(str(a), '') for a in args)
                return re.sub(r'{[A-z_][A-z0-9_]*}', r'%s', self._pattern) % args
            except TypeError:
                return None

        # We need to find the keys from kwargs that occur in our pattern.
        # Unknown keys are pushed to the query string.
        url_kwargs = dict(((k, quote_plus(str(v), '')) for k, v in list(kwargs.items()) if k in self._keywords))
        # this is quoted by urlencode
        qs_kwargs = dict(((k, v) for k, v in list(kwargs.items()) if k not in self._keywords))

        query = '?' + urlencode(qs_kwargs) if qs_kwargs else ''

        # try to fill defaults
        if func is not None and len(url_kwargs.items()) < len(re.findall('{[A-z_][A-z0-9_]*}', self._pattern)):
            defaults = self.get_default_args(func)
            for k, v in defaults.items():
                if k in url_kwargs or k not in self._keywords:
                    continue
                url_kwargs[k] = v

        try:
            return self._pattern.format(**url_kwargs) + query
        except KeyError:
            return None

    @staticmethod
    def get_default_args(func):
        """
        returns a dictionary of arg_name:default_values for the input function
        """
        if sys.version_info.major < 3:
            args, varargs, keywords, defaults = inspect.getargspec(func)
            return dict(zip(args[-len(defaults):], defaults))

        signature = inspect.signature(func)
        return {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

    def __str__(self):
        return "Rule(pattern=%s, keywords=%s)" % (self._pattern, ",".join([str(x[0]) + ":" + str(x[1]) for x in self._keywords]))


def try_convert(value):
    """
    Try to convert to some common types
    :param value: the string to convert
    :type value: str
    """
    # for some of these, they are simplistic and not the generally preferred way
    # this is a special case, so I don't care

    # try to convert to int
    if all(x.isdigit() for x in value):
        return int(value)

    # try to convert to float. We've already check ints, so just try/except
    try:
        return float(value)
    except:
        pass

    # try to convert to bool
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False

    # the original is str, so we can "convert" to str by just returning
    return value
