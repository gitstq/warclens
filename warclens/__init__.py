"""WarcLens — 零依赖 WARC 归档解析与完整性取证工具箱.

WarcLens 是一个纯 Python 标准库实现的 WARC (ISO 28500) 工具箱，专注于：

* 流式解析 ``.warc`` / ``.warc.gz`` 归档，内存占用与文件大小无关；
* 校验 WARC-Block-Digest / WARC-Payload-Digest 的完整性；
* 从归档中提取 URL、MIME、HTTP 状态、时间线与重复内容；
* 同时提供命令行工具与可嵌入的 Python 库接口。

设计原则：零第三方依赖、离线优先、确定性输出、优雅处理损坏数据。

WarcLens is a dependency-free, offline-first toolkit for parsing and
auditing WARC (ISO 28500) web archives with the Python standard library only.

示例 / Quick example::

    from warclens import WARCReader

    with WARCReader("capture.warc.gz") as reader:
        for record in reader:
            print(record.warc_type, record.warc_target_uri)
"""

from .audit import AuditReport, Issue, audit_reader
from .digest import compute_block_digest, encode_digest, verify_digest
from .parser import WARCParseError, WARCRecord, WARCReader, iter_records
from .report import to_csv, to_json, to_markdown

__version__ = "1.0.0"
__all__ = [
    "WARCReader",
    "WARCRecord",
    "WARCParseError",
    "iter_records",
    "compute_block_digest",
    "encode_digest",
    "verify_digest",
    "audit_reader",
    "AuditReport",
    "Issue",
    "to_json",
    "to_csv",
    "to_markdown",
    "__version__",
]
