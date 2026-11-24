"""流式 WARC 解析器.

以单遍、常量内存方式解析 WARC (ISO 28500) 记录。支持：

* 未压缩 ``.warc`` 与 gzip ``.warc.gz``（自动嗅探魔数，透明解压）；
* WARC/0.18、WARC/1.0、WARC/1.1 版本行；
* 头字段大小写不敏感访问；
* 损坏记录的优雅降级（严格模式抛错，宽松模式收集告警）。

实现仅依赖 Python 标准库。解析器一次只在内存中保留一条记录，
因此内存占用与归档文件大小无关。
"""

from __future__ import annotations

import gzip
import io
import os
from dataclasses import dataclass, field
from typing import BinaryIO, Dict, Iterator, List, Optional, Union

# WARC 记录之间以 CRLF CRLF 分隔；头与内容之间以一个空行分隔。
_CRLF = b"\r\n"
_SUPPORTED_VERSIONS = ("WARC/0.18", "WARC/1.0", "WARC/1.1")
_GZIP_MAGIC = b"\x1f\x8b"


class WARCParseError(ValueError):
    """在严格模式下遇到损坏或不合规的 WARC 记录时抛出。"""


@dataclass
class WARCRecord:
    """单条 WARC 记录.

    属性：
        version: 版本行，例如 ``WARC/1.0``。
        headers: 头字段字典，键统一为小写。
        content: 内容块字节（长度由 Content-Length 指定）。
        offset: 记录起始字节偏移（压缩流中为解压后偏移）。
        warnings: 解析该记录时产生的非致命告警。
    """

    version: str
    headers: Dict[str, str] = field(default_factory=dict)
    content: bytes = b""
    offset: int = 0
    warnings: List[str] = field(default_factory=list)

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """大小写不敏感地读取头字段。"""
        return self.headers.get(name.lower(), default)

    # --- 常用头字段的便捷属性 -------------------------------------------
    @property
    def warc_type(self) -> str:
        return (self.get("warc-type") or "").lower()

    @property
    def warc_target_uri(self) -> str:
        return self.get("warc-target-uri") or ""

    @property
    def warc_date(self) -> str:
        return self.get("warc-date") or ""

    @property
    def warc_record_id(self) -> str:
        return self.get("warc-record-id") or ""

    @property
    def content_type(self) -> str:
        return self.get("content-type") or ""

    @property
    def content_length(self) -> int:
        """头中声明的 Content-Length（非实际内容长度）。"""
        raw = self.get("content-length")
        if raw is None:
            return 0
        try:
            return int(raw.strip())
        except (TypeError, ValueError):
            return 0

    @property
    def actual_length(self) -> int:
        """实际读取到的内容块长度。"""
        return len(self.content)

    @property
    def is_complete(self) -> bool:
        """声明长度与实际长度是否一致且无解析告警。"""
        return self.content_length == self.actual_length and not self.warnings

    def __repr__(self) -> str:  # pragma: no cover - 仅调试展示
        return (
            f"WARCRecord(version={self.version!r}, type={self.warc_type!r}, "
            f"uri={self.warc_target_uri!r}, bytes={self.actual_length})"
        )


def _open_stream(source: Union[str, os.PathLike, BinaryIO]) -> BinaryIO:
    """打开文件/流，自动识别 gzip 并返回二进制流。

    传入文件对象时原样返回（不负责关闭）。传入路径时以只读二进制打开，
    并按魔数决定是否用 :mod:`gzip` 透明解压。
    """
    if hasattr(source, "read"):
        return source  # type: ignore[return-value]

    path = os.fspath(source)  # type: ignore[arg-type]
    with open(path, "rb") as probe:
        magic = probe.read(2)
    if magic == _GZIP_MAGIC:
        return gzip.open(path, "rb")
    return open(path, "rb")


def _read_version_line(stream: BinaryIO) -> Optional[bytes]:
    """读取下一个非空行作为候选版本行；EOF 返回 None。

    记录之间可能存在额外的 CRLF，这里统一跳过空行。
    """
    while True:
        line = stream.readline()
        if line == b"":
            return None
        if line.strip() == b"":
            continue
        return line.rstrip(b"\r\n")


def _parse_headers(stream: BinaryIO) -> Dict[str, str]:
    """读取头块，直到遇到空行。键统一小写、值去除两端空白。"""
    headers: Dict[str, str] = {}
    while True:
        line = stream.readline()
        if line in (b"", _CRLF, b"\n"):
            break
        if b":" not in line:
            continue
        key, _, value = line.partition(b":")
        headers[key.decode("latin-1").strip().lower()] = value.decode("latin-1").strip()
    return headers


def _record_separator(stream: BinaryIO) -> None:
    """消费内容块之后的 CRLF CRLF 记录分隔符（宽松处理 LF）。"""
    # 最多两个空行；读到非 CRLF 行时回退不现实（流不可回退），
    # 因此只消费由 \r\n / \n 组成的空行，遇到其它内容即停止。
    consumed = 0
    while consumed < 2:
        line = stream.readline()
        if line == b"":
            break
        if line.strip() == b"":
            consumed += 1
            continue
        break


def iter_records(
    source: Union[str, os.PathLike, BinaryIO],
    *,
    strict: bool = False,
) -> Iterator[WARCRecord]:
    """逐条产出 :class:`WARCRecord`。

    参数:
        source: 归档路径或二进制文件对象。
        strict: 为 True 时，损坏记录抛出 :class:`WARCParseError`；
            为 False 时，尽量解析并在 ``record.warnings`` 中记录问题。

    产生:
        每条记录依次 yield，内存占用保持常量级。
    """
    stream = _open_stream(source)
    owns = not hasattr(source, "read")
    offset = 0
    try:
        while True:
            version_bytes = _read_version_line(stream)
            if version_bytes is None:
                break
            version = version_bytes.decode("latin-1").strip()
            warnings: List[str] = []
            if version not in _SUPPORTED_VERSIONS:
                msg = f"不支持的版本行: {version!r}"
                if strict:
                    raise WARCParseError(msg)
                warnings.append(msg)

            headers = _parse_headers(stream)
            raw_len = headers.get("content-length")
            try:
                declared = int(raw_len) if raw_len is not None else 0
            except (TypeError, ValueError):
                declared = 0
                msg = f"无效 Content-Length: {raw_len!r}"
                if strict:
                    raise WARCParseError(msg)
                warnings.append(msg)

            if declared < 0:
                msg = f"负 Content-Length: {declared}"
                if strict:
                    raise WARCParseError(msg)
                warnings.append(msg)
                declared = 0

            content = stream.read(declared)
            if len(content) != declared:
                msg = f"内容截断: 声明 {declared} 字节, 实际 {len(content)} 字节"
                if strict:
                    raise WARCParseError(msg)
                warnings.append(msg)

            record = WARCRecord(
                version=version,
                headers=headers,
                content=content,
                offset=offset,
                warnings=warnings,
            )
            offset += len(version_bytes) + 2 + declared
            _record_separator(stream)
            yield record
    finally:
        if owns:
            stream.close()


class WARCReader:
    """WARC 归档读取器，支持迭代、上下文管理与一次性读取。

    示例::

        with WARCReader("capture.warc.gz") as reader:
            for record in reader:
                print(record.warc_type, record.warc_target_uri)
    """

    def __init__(
        self,
        source: Union[str, os.PathLike, BinaryIO],
        *,
        strict: bool = False,
    ) -> None:
        self.source = source
        self.strict = strict

    def __iter__(self) -> Iterator[WARCRecord]:
        return iter_records(self.source, strict=self.strict)

    def read_all(self) -> List[WARCRecord]:
        """将所有记录读入内存（适合小归档；大归档请用迭代器）。"""
        return list(self)

    def __enter__(self) -> "WARCReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None
