from .request import Request
from .client import send
from .response import Response


async def request(
    method: str,
    url: str,
    *,
    params=None, headers=None, json=None, data=None, cookies=None,
    connect_timeout: float = 5.0,
    read_timeout: float = 30.0,
    retries: int = 3,
) -> Response:
    req = Request(
        method,
        url,
        headers=headers,
        params=params,
        json=json,
        data=data,
        cookies=cookies,
    )
    return await send(req, retries=retries, connect_timeout=connect_timeout, read_timeout=read_timeout)

async def get(url: str, **kwargs) -> Response:
    return await request("GET", url, **kwargs)

async def post(url: str, **kwargs) -> Response:
    return await request("POST", url, **kwargs)

async def put(url: str, **kwargs) -> Response:
    return await request("PUT", url, **kwargs)

async def delete(url: str, **kwargs) -> Response:
    return await request("DELETE", url, **kwargs)

async def patch(url: str, **kwargs) -> Response:
    return await request("PATCH", url, **kwargs)

async def head(url: str, **kwargs) -> Response:
    return await request("HEAD", url, **kwargs)

