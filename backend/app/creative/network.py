"""Bounded, no-redirect HTTP with DNS validation and numeric-address pinning.

No proxy environment variables are consumed. TLS verifies the original hostname.
Local development requires both config opt-in and an exact server-side loopback authority.
Output downloads never use the development exception or model credentials.
"""
import http.client
import ipaddress
import json
import os
import queue
import socket
import ssl
import threading
import time
from typing import Any
from urllib.parse import urlsplit

from app.services.content import Problem


def addresses(host: str, port: int, timeout: float) -> list[str]:
    result: queue.Queue[Any] = queue.Queue()

    def resolve() -> None:
        try:
            result.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        records = result.get(timeout=timeout)
    except queue.Empty as error:
        raise Problem(504, "MODEL_TIMEOUT", "解析模型地址超时，请稍后手动重试。") from error
    if not records:
        raise Problem(502, "MODEL_UNREACHABLE", "无法解析模型地址，请检查服务配置。")
    return list(dict.fromkeys(str(record[4][0]) for record in records))


def request_bytes(url: str, *, payload: dict[str, Any] | None = None, token: str | None = None,
                  allow_local: bool = False, download: bool = False, maximum: int = 1024 * 1024,
                  timeout: float = 60) -> tuple[bytes, str]:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        authority = f"{host}:{port}"
        dev = (not download and allow_local and authority in
               os.getenv("MANJU_MODEL_DEV_AUTHORITIES", "").split(","))
        if (not host or parsed.username or parsed.password or parsed.fragment or
            any(ord(c) < 33 for c in url) or len(url) > 4096 or
            parsed.scheme != "https" and not (dev and parsed.scheme == "http") or
            not download and parsed.query):
            raise ValueError()
    except ValueError as error:
        raise Problem(422, "UNSAFE_ENDPOINT", "模型或图片地址不符合安全要求。") from error
    started = time.monotonic()
    if os.getenv("MANJU_MODEL_DEV_ONLY", "false").lower() == "true" and not dev:
        raise Problem(403, "DEV_ENDPOINT_ONLY", "当前验证进程只允许明确列出的本机测试端点。")
    ips = addresses(host, port, min(timeout, 10))
    for ip in ips:
        address = ipaddress.ip_address(ip)
        if dev:
            if not address.is_loopback:
                raise Problem(422, "UNSAFE_ENDPOINT", "开发白名单仅允许loopback地址。")
            continue
        if (address.is_multicast or address.is_reserved or "%" in ip or
            getattr(address, "sixtofour", None) or getattr(address, "teredo", None) or
            not address.is_global):
            raise Problem(422, "UNSAFE_ENDPOINT", "禁止请求内网、链路本地或元数据地址。")
    # Connect directly to the checked numeric address: no second DNS lookup, no fallback/retry.
    address = ipaddress.ip_address(ips[0])
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    sock: socket.socket | None = None
    try:
        sock = socket.socket(socket.AF_INET6 if address.version == 6 else socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(max(0.01, timeout - (time.monotonic() - started)))
        sock.connect((str(address), port))
        if parsed.scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        sock.settimeout(max(0.01, timeout - (time.monotonic() - started)))
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        if body is not None and len(body) > 2 * 1024 * 1024:
            raise Problem(413, "INPUT_TOO_LARGE", "本集内容过大，请减少单次创作范围。")
        headers = {"Accept": "image/*" if download else "application/json", "Accept-Encoding": "identity"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token and not download:
            if "\r" in token or "\n" in token:
                raise Problem(503, "MODEL_NOT_CONFIGURED", "服务端模型密钥格式不正确。")
            headers["Authorization"] = "Bearer " + token
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection.request("POST" if payload is not None else "GET", path, body=body, headers=headers)
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise Problem(502, "MODEL_REDIRECT", "服务返回了重定向；请配置最终地址。")
        if response.status in (401, 403):
            raise Problem(502, "MODEL_AUTH", "模型认证失败，请检查服务端密钥与权限。")
        if response.status == 429:
            raise Problem(429, "MODEL_RATE_LIMIT", "模型服务限流，请稍后手动重试。")
        if not 200 <= response.status < 300:
            raise Problem(502, "PROVIDER_ERROR", "模型服务请求失败，请检查协议或稍后手动重试。")
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise Problem(502, "INVALID_MODEL_OUTPUT", "暂不支持压缩的模型响应。")
        length = response.getheader("Content-Length")
        if length and (not length.isdecimal() or int(length) > maximum):
            raise Problem(413, "RESPONSE_TOO_LARGE", "模型响应超过大小限制。")
        chunks: list[bytes] = []
        count = 0
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError()
            sock.settimeout(remaining)
            chunk = response.read1(min(65536, maximum + 1 - count))
            if not chunk:
                break
            count += len(chunk)
            if count > maximum:
                raise Problem(413, "RESPONSE_TOO_LARGE", "模型响应超过大小限制。")
            chunks.append(chunk)
        if length and count != int(length):
            raise Problem(502, "INVALID_MODEL_OUTPUT", "模型响应不完整，请手动重试。")
        return b"".join(chunks), response.getheader("Content-Type", "").split(";")[0].lower()
    except TimeoutError as error:
        raise Problem(504, "MODEL_TIMEOUT", "模型请求超时，未自动重试。重试可能产生额外费用。") from error
    except (OSError, http.client.HTTPException, ValueError) as error:
        raise Problem(502, "MODEL_UNREACHABLE", "模型连接失败，请检查地址、TLS与服务状态。") from error
    finally:
        connection.close()
        if sock is not None:
            sock.close()
