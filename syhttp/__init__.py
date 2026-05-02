from .api import request, get, post, put, delete, patch, head
from .response import Response
from .cookies import CookieJar
from .exceptions import HTTPError

__version__ = "1.2.2"
__all__ = [
    "request",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "Response",
    "CookieJar",
    "HTTPError",
]