from .api import request, get, post, put, delete, patch, head
from .response import Response
from .cookies import CookieJar

__version__ = "1.0.2"
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
]
