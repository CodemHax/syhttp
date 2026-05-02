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
        if json is not None and data is not None:
            raise ValueError("Cannot set both 'json' and 'data' on the same request.")

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
        copied = Request.__new__(Request)
        copied.method = self.method
        copied.url = self.url
        copied.headers = dict(self.headers)
        copied.params = copy.deepcopy(self.params)
        copied.json = copy.deepcopy(self.json)
        copied.data = copy.deepcopy(self.data)
        copied.cookies = dict(self.cookies)
        copied.manual_host = self.manual_host
        copied.manual_cookie = self.manual_cookie
        return copied

    def has_header(self, name: str) -> bool:
        return any(key.lower() == name.lower() for key in self.headers)

    def set_header_on(self, headers: dict, name: str, value: str) -> None:
        for key in headers:
            if key.lower() == name.lower():
                headers[key] = value
                return
        headers[name] = value

    def set_default_header_on(self, headers: dict, name: str, value: str) -> None:
        if not any(k.lower() == name.lower() for k in headers):
            headers[name] = value

    def set_header(self, name: str, value: str) -> None:
        self.set_header_on(self.headers, name, value)

    def set_default_header(self, name: str, value: str) -> None:
        self.set_default_header_on(self.headers, name, value)

    def build_body(self) -> tuple[bytes, dict]:
        extra: dict = {}

        if self.json is not None:
            if not self.has_header("Content-Type"):
                extra["Content-Type"] = "application/json"
            return vjson.dumps(self.json).encode(), extra

        if isinstance(self.data, bytes):
            return self.data, extra

        if isinstance(self.data, str):
            return self.data.encode(), extra

        if isinstance(self.data, dict):
            if not self.has_header("Content-Type"):
                extra["Content-Type"] = "application/x-www-form-urlencoded"
            return urlparse.urlencode(self.data).encode(), extra

        return b"", extra

    def build_path(self, path: str) -> str:
        if self.params:
            separator = "&" if "?" in path else "?"
            path += separator + urlparse.urlencode(self.params, doseq=True)
        return path

    def to_bytes(self, host: str, path: str) -> bytes:
        body, body_headers = self.build_body()
        path = self.build_path(path)

        headers = dict(self.headers)
        for name, value in body_headers.items():
            self.set_default_header_on(headers, name, value)

        if not self.manual_host:
            self.set_header_on(headers, "Host", host)
        self.set_default_header_on(headers, "User-Agent", "syhttp/1.0")
        self.set_default_header_on(headers, "Accept", "*/*")
        self.set_default_header_on(headers, "Connection", "close")

        if self.cookies and not self.manual_cookie:
            self.set_header_on(
                headers,
                "Cookie",
                "; ".join(f"{k}={v}" for k, v in self.cookies.items()),
            )

        has_cl = any(k.lower() == "content-length" for k in headers)
        if body or has_cl:
            self.set_header_on(headers, "Content-Length", str(len(body)))

        lines = [f"{self.method} {path} HTTP/1.1"]
        for key, val in headers.items():
            lines.append(f"{key}: {val}")

        return ("\r\n".join(lines) + "\r\n\r\n").encode() + body