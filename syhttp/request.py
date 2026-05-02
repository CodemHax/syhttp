import copy
import json as vjson
import urllib.parse as urlparse
from typing import Any, Dict, Union, Optional


class Request:

    def __init__(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ):
        self.method = method.upper()
        self.url = url
        self.headers = dict(headers or {})
        self.params = params or {}
        self.json = json
        self.data = data
        self.cookies = cookies or {}
        self.manual_host = self.has_header("Host")
        self.manual_cookie = self.has_header("Cookie")

    def copy(self) -> "Request":
        copied = Request(
            self.method,
            self.url,
            headers=dict(self.headers),
            params=copy.deepcopy(self.params),
            json=copy.deepcopy(self.json),
            data=copy.deepcopy(self.data),
            cookies=dict(self.cookies),
        )
        copied.manual_host = self.manual_host
        copied.manual_cookie = self.manual_cookie
        return copied

    def has_header(self, name: str) -> bool:
        return any(key.lower() == name.lower() for key in self.headers)

    def set_header(self, name: str, value: str) -> None:
        for key in self.headers:
            if key.lower() == name.lower():
                self.headers[key] = value
                return
        self.headers[name] = value

    def set_default_header(self, name: str, value: str) -> None:
        if not self.has_header(name):
            self.headers[name] = value

    def build_body(self) -> bytes:
        if self.json is not None:
            self.set_default_header("Content-Type", "application/json")
            return vjson.dumps(self.json).encode()

        if isinstance(self.data, bytes):
            return self.data

        if isinstance(self.data, str):
            return self.data.encode()

        if isinstance(self.data, dict):
            self.set_default_header("Content-Type", "application/x-www-form-urlencoded")
            return urlparse.urlencode(self.data).encode()

        return b""

    def build_path(self, path: str) -> str:
        if self.params:
            separator = "&" if "?" in path else "?"
            path += separator + urlparse.urlencode(self.params, doseq=True)
        return path

    def to_bytes(self, host: str, path: str) -> bytes:
        body = self.build_body()
        path = self.build_path(path)

        if not self.manual_host:
            self.set_header("Host", host)
        self.set_default_header("User-Agent", "syhttp/1.0")
        self.set_default_header("Accept", "*/*")
        self.set_default_header("Connection", "close")

        if self.cookies and not self.manual_cookie:
            self.set_header(
                "Cookie",
                "; ".join(f"{key}={value}" for key, value in self.cookies.items()),
            )

        if body or self.has_header("Content-Length"):
            self.set_header("Content-Length", str(len(body)))

        lines = [f"{self.method} {path} HTTP/1.1"]
        for key, val in self.headers.items():
            lines.append(f"{key}: {val}")

        return ("\r\n".join(lines) + "\r\n\r\n").encode() + body
