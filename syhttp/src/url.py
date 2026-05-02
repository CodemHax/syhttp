class URL:
    def __init__(self, raw: str):
        self.scheme, self.host, self.port, self.path = self._parse(raw)

    def _parse(self, raw: str):
        scheme, rest = raw.split("://", 1)

        if "/" in rest:
            host, path = rest.split("/", 1)
            path = "/" + path
        else:
            host = rest
            path = "/"

        if ":" in host:
            host, port = host.split(":", 1)
            try:
                port = int(port)
            except ValueError:
                port = 443 if scheme == "https" else 80
        else:
            port = 443 if scheme == "https" else 80

        return scheme, host, port, path

    def __repr__(self):
        return f"URL({self.scheme}://{self.host}:{self.port}{self.path})"
