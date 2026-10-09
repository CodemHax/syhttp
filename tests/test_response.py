import gzip
import unittest
import zlib

from syhttp.response import Response


class ResponseParsingTests(unittest.TestCase):
    def test_decodes_chunked_body(self):
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n"
            b"5\r\nhello\r\n"
            b"6\r\n world\r\n"
            b"0\r\n\r\n"
        )

        response = Response(raw)
        self.assertEqual(response.content, b"hello world")

    def test_decodes_gzip_content(self):
        payload = gzip.compress(b'{"ok":true}')
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Encoding: gzip\r\n"
            b"\r\n"
            + payload
        )

        response = Response(raw)
        self.assertEqual(response.content, b'{"ok":true}')
        self.assertEqual(response.json(), {"ok": True})

    def test_decodes_deflate_content(self):
        payload = zlib.compress(b"deflate-data")
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Encoding: deflate\r\n"
            b"\r\n"
            + payload
        )

        response = Response(raw)
        self.assertEqual(response.content, b"deflate-data")


if __name__ == "__main__":
    unittest.main()
