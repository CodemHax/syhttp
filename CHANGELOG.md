# Changelog

All notable changes to `syhttp` will be documented in this file.

## [1.2.2] - 2026-05-02
### Fixed
- Prevent `Request` object mutation.
- Fixed chunked decoding issues.
- Improved cookie security mechanisms.

## [1.2.0] - 2026-05-02
### Added
- Added `CookieJar` support for persistent cookies.
- Added new HTTP methods (`patch`, `head`).
- Added improved custom header handling.
### Fixed
- Various bug fixes related to request building and high-level API.

## [1.0.0] - 2026-05-02
### Added
- Initial release of `syhttp`.
- Raw asynchronous HTTP client building without external dependencies.
- Added `URL` Parser for evaluating scheme, host, port, and path.
- Created `Request` Builder supporting `GET`, `POST`, query parameters, JSON, and form URL-encoded data.
- Introduced high-level API methods (`syhttp.get`, `syhttp.post`).
- Added basic `README.md` and `.gitignore` file.

