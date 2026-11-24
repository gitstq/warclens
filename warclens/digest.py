"""WARC 内容摘要（Digest）编解码与校验.

WARC 规范（ISO 28500）使用形如 ``sha1:BASE32DIGEST`` 的摘要表示法：
算法名小写，后接冒号，再接 RFC 4648 Base32 编码（无填充）的摘要值。
例如 ``WARC-Block-Digest: sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ``。

本模块仅依赖标准库 :mod:`hashlib` 与 :mod:`base64`，提供：

* :func:`encode_digest` — 计算并编码摘要字符串；
* :func:`verify_digest` — 校验内容是否与给定摘要匹配；
* :func:`compute_block_digest` — 计算一条 WARC 记录的块摘要。
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

# 常见摘要算法及其输出长度（字节）。
_ALGORITHMS = {
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
    "md5": hashlib.md5,
}


def _base32(data: bytes) -> str:
    """RFC 4648 Base32 编码，去除末尾 ``=`` 填充，大写。"""
    return base64.b32encode(data).decode("ascii").rstrip("=").upper()


def encode_digest(data: bytes, algorithm: str = "sha1") -> str:
    """计算 ``data`` 的摘要并返回 WARC 风格字符串 ``算法:BASE32``。

    参数:
        data: 待摘要的字节内容。
        algorithm: 算法名（sha1/sha256/sha512/md5），不区分大小写。

    抛出:
        ValueError: 当算法不受支持时。
    """
    algo = algorithm.lower().strip()
    if algo.startswith("sha"):
        algo = algo.replace("-", "")
    ctor = _ALGORITHMS.get(algo)
    if ctor is None:
        raise ValueError(f"不支持的摘要算法: {algorithm!r}")
    digest = ctor(data).digest()
    return f"{algo}:{_base32(digest)}"


def parse_digest(value: str) -> Optional[tuple]:
    """解析 WARC 摘要字符串，返回 ``(算法, base32值)`` 元组。

    对不符合 ``算法:值`` 格式的输入返回 ``None``。算法名与值均做
    规范化（小写算法、大写值），以便大小写不敏感地比较。
    """
    if not value or ":" not in value:
        return None
    algo, _, raw = value.partition(":")
    algo = algo.strip().lower().replace("-", "")
    raw = raw.strip().rstrip("=").upper()
    if not algo or not raw:
        return None
    if algo not in _ALGORITHMS:
        return None
    return algo, raw


def verify_digest(data: bytes, expected: str) -> bool:
    """校验 ``data`` 是否与 WARC 摘要字符串 ``expected`` 匹配。

    摘要值比较不区分大小写，并容忍末尾填充 ``=``。无法解析的摘要
    字符串一律判定为 ``False``。
    """
    parsed = parse_digest(expected)
    if parsed is None:
        return False
    algo, expected_raw = parsed
    actual = _base32(_ALGORITHMS[algo](data).digest())
    return actual == expected_raw


def compute_block_digest(content: bytes, algorithm: str = "sha1") -> str:
    """计算内容块的 WARC 摘要字符串（等价于 :func:`encode_digest`）。

    该函数的存在是为了语义清晰：调用方在校验 ``WARC-Block-Digest``
    或 ``WARC-Payload-Digest`` 时可以直接使用本函数，而不必关心编码细节。
    """
    return encode_digest(content, algorithm)


def normalize_digest_header(value: str) -> str:
    """将 WARC 摘要头规范化为 ``算法:BASE32`` 形式。

    某些归档器会在算法后附加 URI（如 ``sha1://example.com/...``），
    本函数提取第一个冒号前的算法与随后的摘要片段。无法规范化时返回原值。
    """
    parsed = parse_digest(value)
    if parsed is None:
        return value
    algo, raw = parsed
    return f"{algo}:{raw}"
