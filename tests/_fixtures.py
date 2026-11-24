"""测试夹具：在内存中合成合规的 WARC 归档字节。

仅用于单元测试，不依赖任何真实网页或网络。
"""

from __future__ import annotations

import gzip
from typing import List, Optional

from warclens.digest import encode_digest


def make_record(
    warc_type: str,
    content: bytes,
    *,
    uri: str = "",
    date: str = "2024-01-01T00:00:00Z",
    record_id: str = "<urn:uuid:00000000-0000-0000-0000-000000000001>",
    extra_headers: Optional[dict] = None,
    add_block_digest: bool = True,
    add_payload_digest: bool = False,
    payload_digest: Optional[str] = None,
    content_type: str = "application/octet-stream",
    version: str = "WARC/1.0",
) -> bytes:
    """合成单条 WARC 记录的字节表示。"""
    headers = [
        f"WARC-Type: {warc_type}",
        f"WARC-Record-ID: {record_id}",
        f"WARC-Date: {date}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(content)}",
    ]
    if uri:
        headers.append(f"WARC-Target-URI: {uri}")
    if add_block_digest:
        headers.append(f"WARC-Block-Digest: {encode_digest(content, 'sha1')}")
    if add_payload_digest:
        value = payload_digest if payload_digest is not None else encode_digest(content, "sha1")
        headers.append(f"WARC-Payload-Digest: {value}")
    if extra_headers:
        for key, value in extra_headers.items():
            headers.append(f"{key}: {value}")

    head = version + "\r\n" + "\r\n".join(headers) + "\r\n\r\n"
    return head.encode("latin-1") + content + b"\r\n\r\n"


def make_http_response(body: bytes, status: str = "200") -> bytes:
    """合成 response 记录的内容块（HTTP 状态行 + 头 + 正文）。"""
    head = (
        f"HTTP/1.1 {status} OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
    )
    return head.encode("latin-1") + body


def make_archive(records: List[bytes], gzipped: bool = False) -> bytes:
    """将多条记录拼接为完整归档字节。"""
    blob = b"".join(records)
    return gzip.compress(blob) if gzipped else blob
