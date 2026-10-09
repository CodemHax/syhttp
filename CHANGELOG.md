# Changelog

All notable changes to `syhttp` will be documented in this file.

## [Unreleased]
### Added
- Added pooled keep-alive connection management with configurable pool acquisition timeout.
- Added strict connect/write/read timeout handling and structured retry backoff for idempotent methods.
- Added automatic redirect handling safeguards with typed redirect errors.
- Added response decompression support for `gzip` and `deflate`.
- Added richer exception hierarchy for URL, protocol, TLS, timeout, and network failures.
### Changed
- Improved response parsing robustness for mixed line endings, folded headers, and malformed header protection.
- Switched default request `Connection` header to `keep-alive`.

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
