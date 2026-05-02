import json as vjson


class Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.status_code, self.headers, self.content = self.parse(raw)

    def parse(self, raw: bytes):
        head, _, body = raw.partition(b"\r\n\r\n")
        lines = head.decode().split("\r\n")

        status_code = int(lines[0].split(" ")[1])

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip().lower()] = value.strip()

        return status_code, headers, body

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self):
        return vjson.loads(self.content)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP Error {self.status_code}")

    def __repr__(self):
        return f"<Response [{self.status_code}]>"