import asyncio
from syhttp.src import get, post, put, delete

async def main():
    r = await get("https://httpbin.org/get", params={"q": "hello"})
    print(r, r.json()["args"])

    r = await post("https://httpbin.org/post", json={"name": "alice"})
    print(r, r.json()["json"])

    r = await put("https://httpbin.org/put", json={"x": 1})
    print(r, r.ok)

    r = await delete("https://httpbin.org/delete")
    print(r, r.ok)

asyncio.run(main())