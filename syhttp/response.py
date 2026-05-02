import json as vjson
from typing import Optional
from .exceptions import HTTPError


class Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.status_code, self.reason, self.headers, self.content = self.parse(raw)

    def parse(self, raw: bytes):
        head, _, body = raw.partition(b"\r\n\r\n")
        if not head:
            raise ValueError("Empty HTTP response")

        lines = head.decode("iso-8859-1").split("\r\n")
        status_parts = lines[0].split(" ", 2)
        if len(status_parts) < 2 or not status_parts[0].startswith("HTTP/"):
            raise ValueError(f"Invalid HTTP status line: {lines[0]!r}")

        status_code = int(status_parts[1])
        reason = status_parts[2] if len(status_parts) > 2 else ""

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if key in headers:
                    if isinstance(headers[key], list):
                        headers[key].append(value)
                    else:
                        headers[key] = [headers[key], value]
                else:
                    headers[key] = value

        body = self.decode_chunked(body, headers)

        return status_code, reason, headers, body

    def decode_chunked(self, body: bytes, headers: dict) -> bytes:
        te = headers.get("transfer-encoding", "")
        if isinstance(te, list):
            te = te[-1]
        if te.strip().lower() != "chunked":
            return body

        out = []
        while body:
            crlf = body.find(b"\r\n")
            if crlf == -1:
                break
            size = int(body[:crlf].split(b";")[0].strip(), 16)
            if size == 0:
                break
            chunk_start = crlf + 2
            out.append(body[chunk_start: chunk_start + size])
            body = body[chunk_start + size + 2:]

        return b"".join(out)

    def header(self, name: str) -> Optional[str]:
        val = self.headers.get(name.lower())
        if isinstance(val, list):
            return val[-1]
        return val

    @property
    def encoding(self) -> str:
        content_type = self.headers.get("content-type", "")
        if isinstance(content_type, list):
            content_type = content_type[-1]
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                return part.split("=", 1)[1].strip()
        return "utf-8"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding, errors="replace")

    def json(self):
        return vjson.loads(self.content)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def raise_for_status(self):
        if not self.ok:
            raise HTTPError(self.status_code, self.reason or "error", response=self)

    def __repr__(self):
        return f"<Response [{self.status_code}]>"