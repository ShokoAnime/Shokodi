from abc import abstractmethod
import gzip
import json
import ssl
from io import BytesIO
from socket import timeout

try:
    # noinspection PyUnresolvedReferences
    from urllib.parse import urlparse, quote, unquote_plus, quote_plus, urlencode
    # noinspection PyUnresolvedReferences
    from urllib.request import urlopen, Request
    # noinspection PyUnresolvedReferences
    from urllib.error import HTTPError
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import quote, unquote_plus, quote_plus, urlencode
    # noinspection PyUnresolvedReferences
    from urlparse import urlparse
    # noinspection PyUnresolvedReferences
    from urllib2 import urlopen, Request, HTTPError, URLError

from lib.utils.globalvars import plugin_addon


class BasePythonProxy:
    def __init__(self):
        self.api_key = ''
        self.HTTPError = HTTPError

    def set_temporary_apikey(self, apikey):
        self.api_key = apikey

    @abstractmethod
    def encode(self, value):
        """
        Encodes a string/unicode
        :param value: str or unicode to encode
        :return: encoded str
        """
        pass

    @abstractmethod
    def decode(self, value):
        """
        Decodes a string
        :param value: str
        :return: decoded str or unicode
        """
        pass

    @abstractmethod
    def is_string(self, i):
        pass

    def get_data(self, url, referer, time_out, apikey):
        import lib.error_handler as eh
        headers = {
            'Accept': 'application/json',
            'apikey': apikey,
        }
        if referer is not None:
            referer = quote(self.encode(referer)).replace('%3A', ':')
            if len(referer) > 1:
                headers['Referer'] = referer
        if '127.0.0.1' not in url and 'localhost' not in url:
            headers['Accept-Encoding'] = 'gzip'
        if '/Stream/' in url:
            headers['api-version'] = '1.0'

        req = Request(self.decode(url), headers=headers)
        data = None

        eh.spam('Getting Data ---')
        eh.spam('URL: ', url)
        eh.spam('Headers: ', headers)
        eh.spam('Timeout: ', time_out)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        response = urlopen(req, timeout=int(time_out), context=ctx)
        if response.info().get('Content-Encoding') == 'gzip':
            eh.spam('Got gzipped response. Decompressing')
            try:
                buf = BytesIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                data = self.decode(f.read())
            except:
                from lib.error_handler import ErrorPriority
                eh.exception(ErrorPriority.NORMAL)
        else:
            data = self.decode(response.read())
        response.close()

        eh.spam('Response Body:', data)
        eh.spam('Checking Response for a text error.\n')

        if data is not None and data != '':
            self.parse_possible_error(req, data)

        return data

    def set_parameter(self, url, parameter, value):
        """
        Process a URL to add parameters to the query string
        :param url:
        :param parameter: what to set
        :param value: what to set it to. Do not urlencode it
        :return: the url
        :rtype: basestring
        """
        if value is None or value == '':
            if '?' not in url:
                return url
            array1 = url.split('?')
            if (parameter + '=') not in array1[1]:
                return url
            url = array1[0] + '?'
            array2 = array1[1].split('&')
            for key in array2:
                array3 = key.split('=')
                if array3[0] == parameter:
                    continue
                url += array3[0] + '=' + array3[1] + '&'
            return url[:-1]
        value = quote_plus(self.encode(str(value)))
        if '?' not in url:
            return url + '?' + parameter + '=' + value

        array1 = url.split('?')
        if (parameter + '=') not in array1[1]:
            return url + '&' + parameter + '=' + value

        url = array1[0] + '?'
        array2 = array1[1].split('&')
        array2.append(parameter + '=' + value)

        for key in array2:
            array3 = key.split('=')
            if array3[0] == parameter:
                array3[1] = value
            url += array3[0] + '=' + array3[1] + '&'
        return url[:-1]

    def post_data(self, url, data_in, suppress=False, custom_timeout=int(plugin_addon.getSetting('timeout'))):
        """
        Send a message to the server and wait for a response
        Args:
            url: the URL to send the data to
            data_in: the message to send (in json)
            suppress: swallow the errors
            custom_timeout: if not given timeout from plugin setting will be used

        Returns: The response from the server
        """
        import lib.error_handler as eh
        from lib.error_handler import ErrorPriority
        if data_in is None:
            data_in = b''

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
        }

        apikey = plugin_addon.getSetting('apikey')
        if apikey is not None and apikey != '':
            headers['apikey'] = apikey

        eh.spam('POSTing Data ---')
        eh.spam('URL:', url)
        eh.spam('Headers:', headers)
        eh.spam('POST Body:', data_in)

        req = Request(self.decode(url), self.encode(data_in), headers)

        data_out = None
        try:
            response = urlopen(req, timeout=custom_timeout)
            if response.info().get('Content-Encoding') == 'gzip':
                eh.spam('Got gzipped response. Decompressing')
                try:
                    buf = BytesIO(response.read())
                    f = gzip.GzipFile(fileobj=buf)
                    data_out = self.decode(f.read())
                except:
                    from lib.error_handler import ErrorPriority
                    eh.exception(ErrorPriority.NORMAL)
            else:
                data_out = self.decode(response.read())
            response.close()

            eh.spam('Response Body:', data_out)
            eh.spam('Checking Response for a text error.\n')
            if data_out is not None and data_out != '' and data_out.strip().startswith('{'):
                self.parse_possible_error(req, data_out)
        except timeout:
            # if using very short time out to not wait for response it will throw time out err,
            # but we check if that was intended by checking custom_timeout
            # if it wasn't intended we handle it the old way
            if custom_timeout == int(plugin_addon.getSetting('timeout')):
                eh.exception(ErrorPriority.NORMAL if suppress else ErrorPriority.HIGH)
        except:
            eh.exception(ErrorPriority.NORMAL if suppress else ErrorPriority.HIGH, data_out)
        return data_out

    def parse_parameters(self, input_string):
        """Parses a parameter string starting at the first ? found in inputString

        Argument:
        input_string: the string to be parsed, sys.argv[2] by default

        Returns a dictionary with parameter names as keys and parameter values as values
        """
        parameters = {}
        p1 = input_string.find('?')
        if p1 >= 0:
            split_parameters = input_string[p1 + 1:].split('&')
            for name_value_pair in split_parameters:
                # xbmc.log("parseParameter detected Value: " + str(name_value_pair))
                if (len(name_value_pair) > 0) & ('=' in name_value_pair):
                    pair = name_value_pair.split('=')
                    key = pair[0]
                    value = self.decode(unquote_plus(pair[1]))
                    parameters[key] = value
        return parameters

    @staticmethod
    def quote(url):
        return quote(url, '')

    @staticmethod
    def quote_plus(url):
        return quote_plus(url, '')

    @staticmethod
    def unquote(url):
        return unquote_plus(url)

    @abstractmethod
    def isnumeric(self, value):
        pass

    def get_json(self, url_in):
        """
        use 'get' to return json body as string
        :param url_in:
        :return:
        """
        import lib.error_handler as eh
        from lib.error_handler import ErrorPriority
        try:
            time_out = plugin_addon.getSetting('timeout')
            if self.api_key is None or self.api_key == '':
                apikey = plugin_addon.getSetting('apikey')
            else:
                apikey = self.api_key

            body = self.get_data(url_in, None, time_out, apikey)

        except HTTPError as err:
            raise err
        except:
            eh.exception(ErrorPriority.HIGH)
            body = None
        return body

    def parse_possible_error(self, request, data):
        """

        :param request:
        :type request: Request
        :param data:
        :type data: srt
        :return:
        """
        stream = json.loads(data)
        if 'StatusCode' in stream:
            code = stream.get('StatusCode')
            if code != '200':
                error_msg = code
                if code == '500':
                    error_msg = 'Server Error'
                elif code == '404':
                    error_msg = 'Invalid URL: Endpoint not Found in Server'
                elif code == '503':
                    error_msg = 'Service Unavailable: Check netsh http'
                elif code == '401' or code == '403':
                    error_msg = 'The connection was refused as unauthorized'

                code = self.safe_int(code)
                raise self.http_error(request.get_full_url(), code, error_msg, request.headers)

    @abstractmethod
    def http_error(self, url, code, msg, hdrs):
        pass

    @staticmethod
    def safe_int(obj):
        """
        safe convert type to int to avoid NoneType
        :param obj:
        :return: int
        """
        try:
            if obj is None:
                return 0
            if isinstance(obj, int):
                return obj

            return int(obj)
        except:
            return 0
