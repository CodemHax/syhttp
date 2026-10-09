import asyncio
import contextlib
import logging
import ssl
import urllib.parse as urlparse
from collections import defaultdict, deque
from dataclasses import dataclass
from .url import URL
from .request import Request
from .response import Response
from .cookies import CookieJar
from .exceptions import (
    ConnectTimeout,
    InvalidURL,
    NetworkError,
    PoolTimeout,
    ReadTimeout,
    RemoteProtocolError,
    TLSHandshakeError,
    TooManyRedirects,
    WriteTimeout,
)

logger = logging.getLogger("syhttp")

_SSL_CONTEXT = ssl.create_default_context()
_COOKIE_JAR = CookieJar()
_COOKIE_JAR_LOCK = asyncio.Lock()
_MAX_HEADER_BYTES = 1024 * 128
_IDEMPOTENT_METHODS = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"}


@dataclass
class _Connection:
    key: tuple[str, str, int]
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


class _ConnectionPool:
    def __init__(
        self,
        *,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
    ):
        self._available: dict[tuple[str, str, int], deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_connections)
        self._max_keepalive_connections = max_keepalive_connections
        self._keepalive_expiry = keepalive_expiry

    async def acquire(
        self,
        url: URL,
        *,
        connect_timeout: float,
        pool_timeout: float,
    ) -> _Connection:
        key = (url.scheme, url.host, url.port)
        try:
            async with asyncio.timeout(pool_timeout):
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise PoolTimeout("Timed out waiting for a pooled connection") from exc

        async with self._lock:
            queue = self._available[key]
            now = asyncio.get_running_loop().time()
            while queue:
                reader, writer, created_at = queue.popleft()
                if writer.is_closing() or now - created_at > self._keepalive_expiry:
                    writer.close()
                    continue
                logger.debug("Reusing pooled connection %s://%s:%s", *key)
                return _Connection(key, reader, writer)

        logger.debug("Opening new connection %s://%s:%s", *key)
        try:
            async with asyncio.timeout(connect_timeout):
                reader, writer = await asyncio.open_connection(
                    url.host,
                    url.port,
                    ssl=_SSL_CONTEXT if url.scheme == "https" else None,
                    server_hostname=url.host if url.scheme == "https" else None,
                )
        except TimeoutError as exc:
            self._semaphore.release()
            raise ConnectTimeout(f"Timed out connecting to {url.origin}") from exc
        except ssl.SSLError as exc:
            self._semaphore.release()
            raise TLSHandshakeError(f"TLS handshake failed for {url.origin}: {exc}") from exc
        except OSError as exc:
            self._semaphore.release()
            raise NetworkError(f"Network error connecting to {url.origin}: {exc}") from exc

        return _Connection(key, reader, writer)

    async def release(self, conn: _Connection, *, reusable: bool) -> None:
        try:
            if not reusable or conn.writer.is_closing():
                conn.writer.close()
                with contextlib.suppress(Exception):
                    await conn.writer.wait_closed()
                return

            async with self._lock:
                queue = self._available[conn.key]
                if len(queue) >= self._max_keepalive_connections:
                    conn.writer.close()
                    with contextlib.suppress(Exception):
                        await conn.writer.wait_closed()
                    return

                queue.append((conn.reader, conn.writer, asyncio.get_running_loop().time()))
        finally:
            self._semaphore.release()


_CONNECTION_POOL = _ConnectionPool()


def _split_header_buffer(buffer: bytes) -> tuple[bytes, bytes]:
    marker = b"\r\n\r\n"
    idx = buffer.find(marker)
    if idx != -1:
        return buffer[:idx], buffer[idx + len(marker):]

    marker = b"\n\n"
    idx = buffer.find(marker)
    if idx != -1:
        return buffer[:idx], buffer[idx + len(marker):]

    raise RemoteProtocolError("HTTP response missing header terminator")


async def _read_with_timeout(reader: asyncio.StreamReader, n: int, timeout: float) -> bytes:
    try:
        async with asyncio.timeout(timeout):
            return await reader.read(n)
    except TimeoutError as exc:
        raise ReadTimeout("Timed out while reading response body") from exc


async def _read_exactly_with_timeout(reader: asyncio.StreamReader, n: int, timeout: float) -> bytes:
    if n <= 0:
        return b""
    try:
        async with asyncio.timeout(timeout):
            return await reader.readexactly(n)
    except TimeoutError as exc:
        raise ReadTimeout("Timed out while reading response body") from exc
    except asyncio.IncompleteReadError as exc:
        raise RemoteProtocolError("Response body shorter than declared Content-Length") from exc


async def _read_chunked_body(
    reader: asyncio.StreamReader,
    initial: bytes,
    *,
    read_timeout: float,
) -> bytes:
    body = bytearray()
    buffer = bytearray(initial)

    while True:
        while b"\r\n" not in buffer and b"\n" not in buffer:
            chunk = await _read_with_timeout(reader, 65536, read_timeout)
            if not chunk:
                raise RemoteProtocolError("Unexpected EOF in chunked body")
            buffer.extend(chunk)

        line_end = buffer.find(b"\r\n")
        sep_len = 2
        if line_end == -1:
            line_end = buffer.find(b"\n")
            sep_len = 1
        size_line = bytes(buffer[:line_end]).strip()
        del buffer[: line_end + sep_len]

        try:
            chunk_size = int(size_line.split(b";")[0], 16)
        except ValueError as exc:
            raise RemoteProtocolError(f"Invalid chunk size: {size_line!r}") from exc

        if chunk_size == 0:
            while b"\r\n\r\n" not in buffer and b"\n\n" not in buffer:
                chunk = await _read_with_timeout(reader, 65536, read_timeout)
                if not chunk:
                    break
                buffer.extend(chunk)
            return bytes(body)

        while len(buffer) < chunk_size + 2:
            chunk = await _read_with_timeout(reader, 65536, read_timeout)
            if not chunk:
                raise RemoteProtocolError("Unexpected EOF in chunked body payload")
            buffer.extend(chunk)

        body.extend(buffer[:chunk_size])
        del buffer[:chunk_size]
        if buffer.startswith(b"\r\n"):
            del buffer[:2]
        elif buffer.startswith(b"\n"):
            del buffer[:1]
        else:
            raise RemoteProtocolError("Missing chunk terminator")


def _can_have_body(method: str, status_code: int) -> bool:
    if method.upper() == "HEAD":
        return False
    if 100 <= status_code < 200 or status_code in {204, 304}:
        return False
    return True


def _is_connection_reusable(headers: dict, http_version: str, body_delimited_by_eof: bool) -> bool:
    connection_header = Response.header_from_map(headers, "connection").lower()
    if "close" in connection_header:
        return False
    if http_version == "HTTP/1.0" and "keep-alive" not in connection_header:
        return False
    if body_delimited_by_eof:
        return False
    return True


async def _read_response(
    reader: asyncio.StreamReader,
    *,
    method: str,
    read_timeout: float,
) -> tuple[Response, bool]:
    buffer = bytearray()
    while True:
        if b"\r\n\r\n" in buffer or b"\n\n" in buffer:
            break
        if len(buffer) > _MAX_HEADER_BYTES:
            raise RemoteProtocolError("Response headers exceed maximum size")
        chunk = await _read_with_timeout(reader, 4096, read_timeout)
        if not chunk:
            raise RemoteProtocolError("Connection closed before response headers")
        buffer.extend(chunk)

    head, rest = _split_header_buffer(bytes(buffer))
    status_code, reason, headers = Response.parse_head(head)
    first_line = head.decode("iso-8859-1", errors="replace").replace("\r", "").split("\n", 1)[0]
    http_version = first_line.split(" ", 1)[0].upper()

    has_body = _can_have_body(method, status_code)
    body_delimited_by_eof = False

    if not has_body:
        body = b""
    else:
        transfer_encoding = Response.header_from_map(headers, "transfer-encoding").lower()
        content_length = Response.header_from_map(headers, "content-length")

        if "chunked" in transfer_encoding:
            body = await _read_chunked_body(reader, rest, read_timeout=read_timeout)
        elif content_length:
            try:
                length = int(content_length)
            except ValueError as exc:
                raise RemoteProtocolError(f"Invalid Content-Length: {content_length!r}") from exc
            if length < 0:
                raise RemoteProtocolError("Negative Content-Length is invalid")
            missing = max(0, length - len(rest))
            tail = await _read_exactly_with_timeout(reader, missing, read_timeout)
            body = rest[:length] + tail
        else:
            body_delimited_by_eof = True
            chunks = [rest]
            while True:
                chunk = await _read_with_timeout(reader, 65536, read_timeout)
                if not chunk:
                    break
                chunks.append(chunk)
            body = b"".join(chunks)

    reusable = _is_connection_reusable(headers, http_version, body_delimited_by_eof)
    raw = head + b"\r\n\r\n" + body
    return Response.from_parts(status_code, reason, headers, body, raw=raw), reusable


async def send_once(
    request: Request,
    url: URL,
    connect_timeout: float = 5.0,
    write_timeout: float = 30.0,
    read_timeout: float = 30.0,
    pool_timeout: float = 5.0,
) -> Response:
    conn = await _CONNECTION_POOL.acquire(
        url,
        connect_timeout=connect_timeout,
        pool_timeout=pool_timeout,
    )
    reusable = False
    request_to_send = request.copy()
    response = None

    try:
        async with _COOKIE_JAR_LOCK:
            jar_cookies = _COOKIE_JAR.get(url)

        request_to_send.cookies = {**jar_cookies, **request_to_send.cookies}
        payload = request_to_send.to_bytes(url.host_header, url.path)
        logger.debug(
            "Sending %s request to %s (%d bytes)",
            request_to_send.method,
            request_to_send.url,
            len(payload),
        )

        conn.writer.write(payload)
        try:
            async with asyncio.timeout(write_timeout):
                await conn.writer.drain()
        except TimeoutError as exc:
            raise WriteTimeout(f"Timed out writing request to {url.origin}") from exc

        response, reusable = await _read_response(
            conn.reader,
            method=request_to_send.method,
            read_timeout=read_timeout,
        )
        logger.debug(
            "Received response %d from %s (%d bytes)",
            response.status_code,
            request_to_send.url,
            len(response.content),
        )
    except (ssl.SSLError, OSError) as exc:
        logger.error("Network error for %s: %s", request.url, exc)
        raise NetworkError(f"Network error while sending request to {request.url}: {exc}") from exc
    finally:
        await _CONNECTION_POOL.release(conn, reusable=reusable)

    async with _COOKIE_JAR_LOCK:
        _COOKIE_JAR.update(url, response.headers)

    return response


async def send_with_redirects(
    request: Request,
    url: URL,
    max_redirects: int = 10,
    connect_timeout: float = 5.0,
    write_timeout: float = 30.0,
    read_timeout: float = 30.0,
    pool_timeout: float = 5.0,
) -> Response:
    current_request = request.copy()
    current_url = url

    for redirect_count in range(max_redirects + 1):
        response = await send_once(
            current_request,
            current_url,
            connect_timeout=connect_timeout,
            write_timeout=write_timeout,
            read_timeout=read_timeout,
            pool_timeout=pool_timeout,
        )

        if response.status_code not in (301, 302, 303, 307, 308):
            return response

        location = response.header("location")
        if not location:
            return response
        if redirect_count >= max_redirects:
            raise TooManyRedirects(f"Exceeded redirect limit ({max_redirects}) for {request.url}")

        redirected_url = urlparse.urljoin(current_url.origin + current_url.path, location)
        next_request = current_request.copy()
        next_request.url = redirected_url

        if response.status_code == 303 and next_request.method != "HEAD":
            next_request.method = "GET"
            next_request.json = None
            next_request.data = None
            for key in list(next_request.headers):
                if key.lower() in {"content-length", "content-type"}:
                    del next_request.headers[key]
        elif response.status_code in (301, 302) and next_request.method == "POST":
            next_request.method = "GET"
            next_request.json = None
            next_request.data = None
            for key in list(next_request.headers):
                if key.lower() in {"content-length", "content-type"}:
                    del next_request.headers[key]

        logger.debug("Following redirect %s -> %s", current_url.origin + current_url.path, redirected_url)
        current_request = next_request
        current_url = URL(redirected_url)

    raise TooManyRedirects(f"Exceeded redirect limit ({max_redirects}) for {request.url}")


async def send(
    request: Request,
    max_redirects: int = 10,
    retries: int = 3,
    connect_timeout: float = 5.0,
    write_timeout: float = 30.0,
    read_timeout: float = 30.0,
    pool_timeout: float = 5.0,
    backoff_factor: float = 0.5,
) -> Response:
    if retries < 1:
        raise ValueError("retries must be >= 1")

    try:
        url = URL(request.url)
    except ValueError as exc:
        raise InvalidURL(str(exc)) from exc

    retryable = request.method.upper() in _IDEMPOTENT_METHODS
    last_error = None

    for attempt in range(retries):
        try:
            return await send_with_redirects(
                request,
                url,
                max_redirects=max_redirects,
                connect_timeout=connect_timeout,
                write_timeout=write_timeout,
                read_timeout=read_timeout,
                pool_timeout=pool_timeout,
            )
        except (ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout, NetworkError, TLSHandshakeError) as error:
            last_error = error
            if not retryable or attempt == retries - 1:
                break
            wait = backoff_factor * (2 ** attempt)
            logger.warning("Attempt %d failed (%s), retrying in %.2fs", attempt + 1, error, wait)
            await asyncio.sleep(wait)
        except (TooManyRedirects, RemoteProtocolError):
            raise

    if last_error is not None:
        raise last_error
    raise RemoteProtocolError("Request failed without an explicit error")