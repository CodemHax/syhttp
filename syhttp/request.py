import json as vjson
import urllib.parse as urlparse
from typing import Any, Dict, Union, Optional


class Request:

    def __init__(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None, json: Optional[Dict[str, Any]] = None, data: Optional[Union[Dict[str, Any], str, bytes]] = None):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self.json = json
        self.data = data

    def build_body(self) -> bytes:
        if self.json is not None:
            self.headers['Content-Type'] = 'application/json'
            return vjson.dumps(self.json).encode()

        if isinstance(self.data, bytes):
            return self.data

        if isinstance(self.data, str):
            return self.data.encode()

        if isinstance(self.data, dict):
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            return urlparse.urlencode(self.data).encode()

        return b""


    def build_path(self, path: str) -> str:
        if self.params:
            path += "?" + urlparse.urlencode(self.params)
        return path


    def to_bytes(self, host: str, path: str) -> bytes:
        body = self.build_body()
        path = self.build_path(path)


        self.headers.setdefault('Host', host)
        self.headers.setdefault("User-Agent", "syhttp/1.0")
        self.headers.setdefault("Accept", "*/*")
        self.headers.setdefault("Connection", "close")

        if body:
            self.headers["Content-Length"] = str(len(body))

        lines = [f"{self.method} {path} HTTP/1.1"]
        for key, val in self.headers.items():
            lines.append(f"{key}: {val}")

        return ("\r\n".join(lines) + "\r\n\r\n").encode() + body