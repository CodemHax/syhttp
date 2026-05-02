from http.cookies import SimpleCookie
from typing import Dict, Optional

from .url import URL


class CookieJar:
    def __init__(self):
        self.cookies: Dict[str, Dict[str, str]] = {}

    def get(self, url: URL) -> Dict[str, str]:
        cookies: Dict[str, str] = {}

        for domain, values in self.cookies.items():
            if url.host == domain or url.host.endswith("." + domain):
                cookies.update(values)

        return cookies

    def update(self, url: URL, headers) -> None:
        set_cookie = headers.get("set-cookie")
        if not set_cookie:
            return

        if isinstance(set_cookie, str):
            set_cookie = [set_cookie]

        for header in set_cookie:
            cookie = SimpleCookie()
            cookie.load(header)

            for name, morsel in cookie.items():
                domain: Optional[str] = morsel["domain"] or url.host
                domain = domain.lstrip(".").lower()
                self.cookies.setdefault(domain, {})[name] = morsel.value
