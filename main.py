import asyncio
import json

from syhttp import delete, get, post, put


async def handle_client(reader, writer):
    raw = await reader.read(65536)
    request_text = raw.decode(errors="replace")
    head, _, body = request_text.partition("\r\n\r\n")
    request_line = head.splitlines()[0]
    method, path, _ = request_line.split(" ", 2)

    headers = {}
    for line in head.splitlines()[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()

    extra_headers = []
    if path.startswith("/get"):
        response_body = b'{"ok": true, "method": "GET"}'
    elif path == "/post":
        response_body = json.dumps(
            {"ok": True, "method": "POST", "body": body}
        ).encode()
    elif path == "/put":
        response_body = b'{"ok": true, "method": "PUT"}'
    elif path == "/delete":
        response_body = b'{"ok": true, "method": "DELETE"}'
    elif path == "/cookies/set":
        response_body = b'{"ok": true}'
        extra_headers.append("Set-Cookie: theme=dark; Path=/")
    elif path == "/cookies":
        cookie = headers.get("cookie", "")
        response_body = json.dumps({"cookie": cookie}).encode()
    else:
        response_body = b'{"ok": false}'

    response_headers = [
        "HTTP/1.1 200 OK",
        "Content-Type: application/json",
        f"Content-Length: {len(response_body)}",
        "Connection: close",
        *extra_headers,
        "",
        "",
    ]
    writer.write("\r\n".join(response_headers).encode() + response_body)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()
    base_url = f"http://{host}:{port}"

    try:
        get_response = await get(f"{base_url}/get", params={"q": "hello"})
        print("GET:", get_response, get_response.json())

        post_response = await post(f"{base_url}/post", json={"name": "alice"})
        print("POST:", post_response, post_response.json())

        put_response = await put(f"{base_url}/put", json={"x": 1})
        print("PUT:", put_response, put_response.ok)

        delete_response = await delete(f"{base_url}/delete")
        print("DELETE:", delete_response, delete_response.ok)

        manual_cookie = await get(
            f"{base_url}/cookies",
            cookies={"session": "abc123"},
        )
        print("Manual cookies:", manual_cookie.json())

        await get(f"{base_url}/cookies/set")
        saved_cookie = await get(f"{base_url}/cookies")
        print("Saved cookies:", saved_cookie.json())
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
