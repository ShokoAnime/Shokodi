from lib.proxy.python.python_proxy import BasePythonProxy


class Python3Proxy(BasePythonProxy):
    def __init__(self):
        BasePythonProxy.__init__(self)

    def encode(self, i):
        try:
            if isinstance(i, bytes):
                return i
            elif isinstance(i, str):
                return i.encode('utf-8')
            else:
                return str(i).encode('utf-8')
        except:
            # nt.error('Unicode Error', error_type='Unicode Error')
            return ''

    def decode(self, i):
        try:
            if isinstance(i, bytes):
                return i.decode('utf-8')
            elif isinstance(i, str):
                return i
            else:
                return str(i)
        except:
            # error('Unicode Error', error_type='Unicode Error')
            return ''

    def is_string(self, i):
        return isinstance(i, str)

    def isnumeric(self, value):
        # noinspection PyUnresolvedReferences
        return str(value).isnumeric()

    def http_error(self, url, code, msg, hdrs):
        from urllib.error import HTTPError
        return HTTPError(url, code, msg, hdrs, fp=None)
