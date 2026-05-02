from typing import Dict, Optional
from .url import URL


class CookieJar:
    def __init__(self):
        self.cookies: Dict[str, Dict[str, dict]] = {}

    def get(self, url: URL) -> Dict[str, str]:
        result: Dict[str, str] = {}
        is_secure = url.scheme == "https"

        for domain, path_map in self.cookies.items():
            host_matches = url.host == domain or url.host.endswith("." + domain)
            if not host_matches:
                continue

            for cookie_path, jar in path_map.items():
                path_matches = url.path == cookie_path or url.path.startswith(
                    cookie_path.rstrip("/") + "/"
                )
                if not path_matches:
                    continue

                for name, meta in jar.items():
                    if meta["secure"] and not is_secure:
                        continue
                    result[name] = meta["value"]

        return result

    def update(self, url: URL, headers) -> None:
        set_cookie = headers.get("set-cookie")
        if not set_cookie:
            return

        if isinstance(set_cookie, str):
            set_cookie = [set_cookie]

        for header in set_cookie:
            parts = [p.strip() for p in header.split(";")]
            if not parts or "=" not in parts[0]:
                continue

            name, _, value = parts[0].partition("=")
            name = name.strip()
            value = value.strip()

            attrs: Dict[str, str] = {}
            for attr in parts[1:]:
                if "=" in attr:
                    k, _, v = attr.partition("=")
                    attrs[k.strip().lower()] = v.strip()
                else:
                    attrs[attr.strip().lower()] = "true"

            domain: Optional[str] = attrs.get("domain") or url.host
            domain = domain.lstrip(".").lower()

            cookie_path: str = attrs.get("path", "/")
            secure: bool = "secure" in attrs

            self.cookies.setdefault(domain, {}).setdefault(cookie_path, {})[name] = {
                "value": value,
                "secure": secure,
            }