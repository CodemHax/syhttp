import urllib.parse as urlparse


class URL:
    def __init__(self, raw: str):
        self.raw = raw
        self.scheme, self.host, self.port, self.path = self._parse(raw)

    def _parse(self, raw: str):
        parsed = urlparse.urlsplit(raw)
        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
        if not parsed.hostname:
            raise ValueError(f"Invalid URL: {raw!r}")

        port = parsed.port
        if port is None:
            port = 443 if scheme == "https" else 80

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        return scheme, parsed.hostname, port, path

    @property
    def origin(self) -> str:
        default_port = 443 if self.scheme == "https" else 80
        host = f"[{self.host}]" if ":" in self.host else self.host
        if self.port == default_port:
            return f"{self.scheme}://{host}"
        return f"{self.scheme}://{host}:{self.port}"

    @property
    def host_header(self) -> str:
        default_port = 443 if self.scheme == "https" else 80
        host = f"[{self.host}]" if ":" in self.host else self.host
        if self.port == default_port:
            return host
        return f"{host}:{self.port}"

    def __repr__(self):
        return f"URL({self.origin}{self.path})"
