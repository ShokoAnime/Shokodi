from lib.proxy.python.python_proxy import BasePythonProxy


# noinspection PyUnresolvedReferences
class Python2Proxy(BasePythonProxy):
    def __init__(self):
        BasePythonProxy.__init__(self)

    def encode(self, i):
        try:
            if isinstance(i, str):
                return i
            elif isinstance(i, unicode):
                return i.encode('utf-8')
            else:
                return str(i)
        except:
            pass  # nt.error('Unicode Error', error_type='Unicode Error')
            return ''

    def decode(self, i):
        try:
            if isinstance(i, bytes):
                return i.decode('utf-8')
            elif isinstance(i, unicode):
                return i
            else:
                return unicode(i)
        except:
            # error('Unicode Error', error_type='Unicode Error')
            return ''

    def is_string(self, i):
        return isinstance(i, (str, unicode, basestring))

    def isnumeric(self, value):
        return unicode(value).isnumeric()

    def http_error(self, url, code, msg, hdrs):
        # noinspection PyArgumentList
        from urllib2 import HTTPError
        return HTTPError(code, msg)
