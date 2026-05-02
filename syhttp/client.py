import asyncio
from .request import Request
from .response import Response
from .url import URL
import ssl


async def send(request: Request) ->  Response:
      url = URL(request.url)

      if url.scheme == "https":
          ctx = ssl.create_default_context()
          reader, writer = await asyncio.open_connection(url.host, url.port, ssl=ctx)
      else:
          reader, writer = await asyncio.open_connection(url.host, url.port)

      writer.write(request.to_bytes(url.host, url.path))
      await writer.drain()

      raw = b""
      while True:
          data = await reader.read(1024)
          if not data:
              break
          raw += data

      writer.close()
      try:
          await writer.wait_closed()
      except ssl.SSLError:
          pass

      return Response(raw)
