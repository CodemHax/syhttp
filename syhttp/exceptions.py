class SyHTTPError(Exception):
    """Base exception for syhttp."""


class InvalidURL(SyHTTPError):
    pass


class NetworkError(SyHTTPError):
    pass


class TimeoutError(SyHTTPError):
    pass


class ConnectTimeout(TimeoutError):
    pass


class ReadTimeout(TimeoutError):
    pass


class WriteTimeout(TimeoutError):
    pass


class PoolTimeout(TimeoutError):
    pass


class TLSHandshakeError(NetworkError):
    pass


class RemoteProtocolError(SyHTTPError):
    pass


class RedirectError(SyHTTPError):
    pass


class TooManyRedirects(RedirectError):
    pass


class HTTPError(SyHTTPError):
    def __init__(self, status_code: int, message: str, response=None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response = response