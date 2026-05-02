import asyncio
from .request import Request
from .client import send
from .response import Response
from typing import Any, Dict, Optional, Union


async def request(
    method: str,
    url: str,
    *,
    params:  Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    json:    Optional[Any] = None,
    data:    Optional[Union[str, bytes, Dict]] = None,
    timeout: float = 30.0,
) -> Response:
    req = Request(method, url, headers=headers, params=params, json=json, data=data)
    return await asyncio.wait_for(send(req), timeout=timeout)


async def get(url: str, **kwargs) -> Response:
    return await request("GET", url, **kwargs)

async def post(url: str, **kwargs) -> Response:
    return await request("POST", url, **kwargs)

async def put(url: str, **kwargs) -> Response:
    return await request("PUT", url, **kwargs)

async def delete(url: str, **kwargs) -> Response:
    return await request("DELETE", url, **kwargs)