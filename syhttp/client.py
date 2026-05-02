import asyncio
import ssl
import urllib.parse as urlparse
from .url import URL
from .request import Request
from .response import Response
from .cookies import CookieJar


_SSL_CONTEXT = ssl.create_default_context()
_COOKIE_JAR = CookieJar()


async def send_once(
    request: Request,
    url: URL,
    connect_timeout: float = 5.0,
    read_timeout: float = 30.0,
) -> Response:
    if url.scheme == "https":
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(url.host, url.port, ssl=_SSL_CONTEXT),
            timeout=connect_timeout,
        )
    else:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(url.host, url.port),
            timeout=connect_timeout,
        )

    jar_cookies = _COOKIE_JAR.get(url)
    request.cookies = {**jar_cookies, **request.cookies}

    writer.write(request.to_bytes(url.host_header, url.path))
    await writer.drain()

    chunks = []
    while True:
        chunk = await asyncio.wait_for(reader.read(65536), timeout=read_timeout)
        if not chunk:
            break
        chunks.append(chunk)

    writer.close()
    try:
        await writer.wait_closed()
    except ssl.SSLError:
        pass

    response = Response(b"".join(chunks))
    _COOKIE_JAR.update(url, response.headers)
    return response


async def send_with_redirects(
    request: Request,
    url: URL,
    max_redirects: int = 10,
    connect_timeout: float = 5.0,
    read_timeout: float = 30.0,
) -> Response:
    for i in range(max_redirects):
        response = await send_once(request, url, connect_timeout, read_timeout)

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                break

            location = urlparse.urljoin(url.origin + url.path, location)

            request = request.copy()
            request.url = location
            url = URL(location)

            if response.status_code == 303:
                request.method = "GET"
                request.json = None
                request.data = None

            continue

        return response

    raise Exception("Too many redirects")


async def send(
    request: Request,
    max_redirects: int = 10,
    retries: int = 3,
    connect_timeout: float = 5.0,
    read_timeout: float = 30.0,
) -> Response:
    url = URL(request.url)
    last_error = None

    for attempt in range(retries):
        try:
            return await send_with_redirects(
                request, url, max_redirects, connect_timeout, read_timeout
            )
        except (OSError, asyncio.TimeoutError) as e:
            last_error = e
            wait = 2 ** attempt
            print(f"Attempt {attempt + 1} failed ({e}), retrying in {wait}s...")
            await asyncio.sleep(wait)

    raise last_error
