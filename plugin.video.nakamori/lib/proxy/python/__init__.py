import sys

from lib.proxy.python.python_2_proxy import Python2Proxy
from lib.proxy.python.python_3_proxy import Python3Proxy


proxy = Python2Proxy() if sys.version_info[0] < 3 else Python3Proxy()
