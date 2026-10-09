import gzip
import json as vjson
import zlib
from typing import Optional
from .exceptions import HTTPError, RemoteProtocolError


class Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.status_code, self.reason, self.headers, body = self.parse(raw)
        self.content = self.decompress(body, self.headers)

    @classmethod
    def from_parts(
        cls,
        status_code: int,
        reason: str,
        headers: dict,
        body: bytes,
        raw: Optional[bytes] = None,
    ) -> "Response":
        response = cls.__new__(cls)
        response.status_code = status_code
        response.reason = reason
        response.headers = headers
        response.content = cls.decompress(body, headers)
        response.raw = raw if raw is not None else b""
        return response

    @classmethod
    def parse_head(cls, head: bytes) -> tuple[int, str, dict]:
        text = head.decode("iso-8859-1", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        if not lines or not lines[0]:
            raise RemoteProtocolError("Empty HTTP response head")

        status_parts = lines[0].split(" ", 2)
        if len(status_parts) < 2 or not status_parts[0].startswith("HTTP/"):
            raise RemoteProtocolError(f"Invalid HTTP status line: {lines[0]!r}")

        try:
            status_code = int(status_parts[1])
        except ValueError as exc:
            raise RemoteProtocolError(f"Invalid HTTP status code: {status_parts[1]!r}") from exc
        reason = status_parts[2] if len(status_parts) > 2 else ""

        headers = {}
        current_name = None

        for line in lines[1:]:
            if not line:
                continue

            if line.startswith((" ", "\t")):
                if not current_name:
                    raise RemoteProtocolError("Invalid folded header")
                previous = headers[current_name]
                extra = " " + line.strip()
                if isinstance(previous, list):
                    previous[-1] += extra
                else:
                    headers[current_name] = previous + extra
                continue

            if ":" not in line:
                raise RemoteProtocolError(f"Malformed header line: {line!r}")

            key, _, value = line.partition(":")
            name = cls._sanitize_header_name(key)
            safe_value = cls._sanitize_header_value(value.strip())
            current_name = name

            if name in headers:
                if isinstance(headers[name], list):
                    headers[name].append(safe_value)
                else:
                    headers[name] = [headers[name], safe_value]
            else:
                headers[name] = safe_value

        return status_code, reason, headers

    def parse(self, raw: bytes):
        head, body = self.split_head_body(raw)
        status_code, reason, headers = self.parse_head(head)
        body = self.decode_chunked(body, headers)
        return status_code, reason, headers, body

    @staticmethod
    def split_head_body(raw: bytes) -> tuple[bytes, bytes]:
        if b"\r\n\r\n" in raw:
            head, _, body = raw.partition(b"\r\n\r\n")
            return head, body
        if b"\n\n" in raw:
            head, _, body = raw.partition(b"\n\n")
            return head, body
        raise RemoteProtocolError("HTTP response missing header terminator")

    @staticmethod
    def _sanitize_header_name(name: str) -> str:
        clean = name.strip().lower()
        if not clean:
            raise RemoteProtocolError("Empty header name")
        if any(ord(ch) < 33 or ord(ch) > 126 or ch in {'"', "(", ")", ",", "/", ":", ";", "<", "=", ">", "?", "@", "[", "\\", "]", "{", "}"} for ch in clean):
            raise RemoteProtocolError(f"Invalid header name: {name!r}")
        return clean

    @staticmethod
    def _sanitize_header_value(value: str) -> str:
        if "\r" in value or "\n" in value:
            raise RemoteProtocolError("Header value contains prohibited control characters")
        return value

    def decode_chunked(self, body: bytes, headers: dict) -> bytes:
        te = self.header_from_map(headers, "transfer-encoding")
        if "chunked" not in te.lower():
            return body

        out = bytearray()
        pos = 0
        body_len = len(body)

        while pos < body_len:
            crlf = body.find(b"\r\n", pos)
            lf = body.find(b"\n", pos)

            if crlf != -1 and (lf == -1 or crlf < lf):
                size_end = crlf
                separator_len = 2
            elif lf != -1:
                size_end = lf
                separator_len = 1
            else:
                raise RemoteProtocolError("Malformed chunk size line")

            size_line = body[pos:size_end].strip()
            try:
                size = int(size_line.split(b";")[0], 16)
            except ValueError as exc:
                raise RemoteProtocolError(f"Invalid chunk size: {size_line!r}") from exc

            data_start = size_end + separator_len
            if body_len < data_start + size:
                raise RemoteProtocolError("Incomplete chunk payload")
            if size == 0:
                return bytes(out)

            chunk_end = data_start + size
            out.extend(body[data_start:chunk_end])
            pos = chunk_end

            if body[pos:pos + 2] == b"\r\n":
                pos += 2
            elif body[pos:pos + 1] == b"\n":
                pos += 1
            else:
                raise RemoteProtocolError("Missing chunk terminator")

        raise RemoteProtocolError("Incomplete chunked response body")

    @classmethod
    def header_from_map(cls, headers: dict, name: str) -> str:
        val = headers.get(name.lower(), "")
        if isinstance(val, list):
            return val[-1]
        return val

    @classmethod
    def decompress(cls, body: bytes, headers: dict) -> bytes:
        content_encoding = cls.header_from_map(headers, "content-encoding").lower()
        if not content_encoding:
            return body

        for encoding in [item.strip() for item in content_encoding.split(",") if item.strip()]:
            if encoding == "gzip":
                try:
                    body = gzip.decompress(body)
                except OSError as exc:
                    raise RemoteProtocolError("Invalid gzip response body") from exc
            elif encoding == "deflate":
                try:
                    body = zlib.decompress(body)
                except zlib.error:
                    try:
                        body = zlib.decompress(body, -zlib.MAX_WBITS)
                    except zlib.error as exc:
                        raise RemoteProtocolError("Invalid deflate response body") from exc
        return body

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