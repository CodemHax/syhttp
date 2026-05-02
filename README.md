# syhttp

A simple, asynchronous Python HTTP client built from scratch using pure `asyncio` streams. `syhttp` gives you an easy-to-use API for crafting completely raw HTTP requests without relying on large third-party libraries like `requests` or `aiohttp`.

## Features

- **No external dependencies**: Pure `asyncio` and Python standard library.
- **`URL` Parser**: A custom URL parser to parse scheme, host, port, and path.
- **`Request` Builder**: Easily construct HTTP `GET` and `POST` requests.
  - Supports query parameters (`params`).
  - Supports JSON payload (`json`).
  - Supports Form URL-encoded data and raw bytes (`data`).
  - Custom headers support.
- **Raw Bytes Extraction**: Compile requests directly to raw HTTP bytes ready to be sent over a socket.

## Installation

You can install `syhttp` locally in your environment via `pip`:

```bash
git clone https://github.com/codemhax/syhttp.git
cd syhttp
pip install -e .
```

## Usage

### Parsing URLs

The `URL` class easily parses HTTP and HTTPS URLs into their components:

```python
from src.url import URL

url = URL("https://httpbin.org/get")
print(url.scheme) # https
print(url.host)   # httpbin.org
print(url.port)   # 443
print(url.path)   # /get
```

### Building Requests

The `Request` class lets you easily build up raw HTTP protocol requests. It automatically computes `Content-Length`, `Content-Type`, and basic headers.

```python
import asyncio
from src.url import URL
from src.request import Request

async def main():
    target_url = URL("https://httpbin.org/post")
    
    # Create an HTTP POST request
    req = Request(
        method="POST",
        url=target_url,
        json={"name": "alice", "role": "admin"}
    )
    
    # Get raw HTTP bytes
    req_bytes = req.to_bytes(host=target_url.host, path=target_url.path)
    print(req_bytes.decode())

    # Open TCP connection
    reader, writer = await asyncio.open_connection(
        target_url.host, target_url.port, ssl=(target_url.scheme == "https")
    )
    
    # Send request
    writer.write(req_bytes)
    await writer.drain()

    # Read response
    response = await reader.read(4096)
    print(response.decode())
    
    writer.close()
    await writer.wait_closed()

asyncio.run(main())
```

### Query Parameters

```python
# Turns into /search?q=syhttp&sort=desc
req = Request("GET", "https://example.com/search", params={"q": "syhttp", "sort": "desc"})
```

### Form URL-Encoded

```python
# Sets Content-Type to application/x-www-form-urlencoded
req = Request("POST", "https://example.com/login", data={"username": "bob", "password": "123"})
```

## Structure

- `src/url.py`: Parsing logic for breaking down endpoint strings.
- `src/request.py`: Logic for building HTTP request lines, headers, and body bytes.
- `main.py`: Example implementation using asyncio streams to open sockets and send/receive data.

## License

MIT License

