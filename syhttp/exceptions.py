class HTTPError(Exception):
    def __init__(self, status_code: int, message: str, response=None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response = response