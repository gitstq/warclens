"""归档内容分析.

在审计之外，对归档做一些只读的统计与取证分析：

* 按记录类型（response/request/metadata/...）计数；
* 提取 URL 与主机并以摘要去重（基于 WARC-Payload-Digest）；
* 解析 response 记录的 HTTP 状态码与内容类型；
* 重建最早/最晚时间戳时间线。

全部为确定性、离线、流式操作。
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import BinaryIO, Dict, Iterable, List, Optional, Set, Union
from urllib.parse import urlparse

from .parser import WARCRecord, iter_records

_STATUS_RE = re.compile(rb"^HTTP/\d(?:\.\d)?\s+(\d{3})", re.IGNORECASE)


@dataclass
class AnalysisReport:
    """归档内容分析汇总。"""

    total_records: int = 0
    type_counts: Dict[str, int] = field(default_factory=dict)
    unique_urls: int = 0
    unique_hosts: int = 0
    duplicate_payloads: int = 0
    status_counts: Dict[str, int] = field(default_factory=dict)
    mime_counts: Dict[str, int] = field(default_factory=dict)
    earliest_date: str = ""
    latest_date: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_records": self.total_records,
            "type_counts": dict(self.type_counts),
            "unique_urls": self.unique_urls,
            "unique_hosts": self.unique_hosts,
            "duplicate_payloads": self.duplicate_payloads,
            "status_counts": dict(self.status_counts),
            "mime_counts": dict(self.mime_counts),
            "earliest_date": self.earliest_date,
            "latest_date": self.latest_date,
        }


def _http_status(content: bytes) -> Optional[str]:
    """从 response 内容块首行解析 HTTP 状态码。"""
    first_line = content.split(b"\r\n", 1)[0].split(b"\n", 1)[0]
    match = _STATUS_RE.match(first_line)
    return match.group(1).decode("ascii") if match else None


def _content_type(content: bytes) -> str:
    """从 response 内容块的 HTTP 头中提取 Content-Type（不含参数）。"""
    header_end = content.find(b"\r\n\r\n")
    if header_end == -1:
        header_end = content.find(b"\n\n")
    if header_end == -1:
        return ""
    header_blob = content[:header_end].decode("latin-1", errors="ignore")
    for line in header_blob.replace("\r", "").split("\n"):
        if line.lower().startswith("content-type:"):
            return line.split(":", 1)[1].strip().split(";", 1)[0].strip().lower()
    return ""


def analyze_records(records: Iterable[WARCRecord]) -> AnalysisReport:
    """分析记录迭代结果并返回 :class:`AnalysisReport`。"""
    report = AnalysisReport()
    type_counter: Counter = Counter()
    status_counter: Counter = Counter()
    mime_counter: Counter = Counter()
    urls: Set[str] = set()
    hosts: Set[str] = set()
    seen_payloads: Set[str] = set()
    duplicates = 0
    dates: List[str] = []

    for record in records:
        report.total_records += 1
        type_counter[record.warc_type or "(unknown)"] += 1

        uri = record.warc_target_uri
        if uri:
            urls.add(uri)
            try:
                host = urlparse(uri).netloc
                if host:
                    hosts.add(host)
            except ValueError:
                pass

        date = record.warc_date
        if date:
            dates.append(date)

        if record.warc_type == "response":
            status = _http_status(record.content)
            if status:
                status_counter[status] += 1
            mime = _content_type(record.content)
            if mime:
                mime_counter[mime] += 1

        digest = record.get("warc-payload-digest") or record.get("warc-block-digest")
        if digest:
            if digest in seen_payloads:
                duplicates += 1
            else:
                seen_payloads.add(digest)

    report.type_counts = dict(type_counter.most_common())
    report.status_counts = dict(status_counter.most_common())
    report.mime_counts = dict(mime_counter.most_common())
    report.unique_urls = len(urls)
    report.unique_hosts = len(hosts)
    report.duplicate_payloads = duplicates
    if dates:
        report.earliest_date = min(dates)
        report.latest_date = max(dates)
    return report


def analyze_archive(
    source: Union[str, os.PathLike, BinaryIO],
    *,
    strict: bool = False,
) -> AnalysisReport:
    """对归档路径或流执行分析并返回 :class:`AnalysisReport`。"""
    return analyze_records(iter_records(source, strict=strict))
