# syhttp

A simple, asynchronous Python HTTP client built from scratch using pure `asyncio` streams. `syhttp` gives you an easy-to-use API for crafting completely raw HTTP requests without relying on large third-party libraries like `requests` or `aiohttp`.

## Features

- **No external dependencies**: Pure `asyncio` and Python standard library.
- **`URL` Parser**: A custom URL parser to parse scheme, host, port, and path.
- **`Request` Builder**: Easily construct HTTP `GET` and `POST` requests.
  - Supports query parameters (`params`).
  - Supports JSON payload (`json`).
  - Supports Form URL-encoded data and raw bytes (`data`).
  - Supports manual cookies (`cookies`).
  - Stores cookies from `Set-Cookie` and sends them on later matching requests.
  - Custom headers support.
- **Raw Bytes Extraction**: Compile requests directly to raw HTTP bytes ready to be sent over a socket.
- **Faster Response Reads**: Reads response bodies in larger chunks and joins them once, avoiding repeated byte copying.

## Installation

You can install `syhttp` locally in your environment via `pip`:

```bash
git clone https://github.com/codemhax/syhttp.git
cd syhttp
pip install -e .
```

## Usage

`syhttp` provides high-level `asyncio` methods for making requests, similar to popular HTTP libraries.

### Basic GET and POST

```python
import asyncio
import syhttp

async def main():
    # GET request
    response = await syhttp.get("https://httpbin.org/get", params={"q": "syhttp"})
    print(response.json())
    
    # POST request with JSON
    response = await syhttp.post(
        "https://httpbin.org/post", 
        json={"name": "alice", "role": "admin"}
    )
    print(response.json())

asyncio.run(main())
```

### Cookies

Pass cookies directly with the `cookies` argument:

```python
response = await syhttp.get(
    "https://httpbin.org/cookies",
    cookies={"session": "abc123"},
)

print(response.json()["cookies"])
```

`syhttp` also stores cookies returned by `Set-Cookie` and sends them on later requests to the same host:

```python
await syhttp.get("https://httpbin.org/cookies/set/theme/dark")

response = await syhttp.get("https://httpbin.org/cookies")
print(response.json()["cookies"])
```

### Parsing URLs Manually

If you only need the URL parser:

```python
from syhttp.url import URL

url = URL("https://httpbin.org/get")
print(url.scheme) # https
print(url.host)   # httpbin.org
print(url.port)   # 443
print(url.path)   # /get
```

### Query Parameters

```python
# Turns into /search?q=syhttp&sort=desc
response = await syhttp.get("https://example.com/search", params={"q": "syhttp", "sort": "desc"})
```

### Form URL-Encoded

```python
# Sets Content-Type to application/x-www-form-urlencoded
response = await syhttp.post("https://example.com/login", data={"username": "bob", "password": "123"})
```

## Structure

- `syhttp/url.py`: Parsing logic for breaking down endpoint strings.
- `syhttp/request.py`: Logic for building HTTP request lines, headers, and body bytes.
- `syhttp/api.py` and `syhttp/client.py`: High-level functions (`get`, `post`, etc.) and the networking engine.
- `syhttp/response.py`: Response parsing and state.
- `syhttp/cookies.py`: Small cookie jar used by the client.

## License

MIT License

