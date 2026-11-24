"""归档完整性审计.

对 WARC 归档执行两类检查：

1. **结构完整性**：记录版本合法、必需头字段存在、Content-Length 与实际
   内容长度一致、无解析告警；
2. **摘要校验**：若记录带有 ``WARC-Block-Digest``，重新计算内容块摘要并
   比对；若 response 记录带 ``WARC-Payload-Digest``，在可提取 HTTP 正文时
   同样校验。

审计结果是 :class:`AuditReport`，包含逐条问题列表与汇总统计，并可序列化
为字典供报告模块生成 JSON/CSV。设计上审计不修改归档、不做网络请求。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import BinaryIO, Dict, List, Optional, Union

from .digest import verify_digest
from .parser import WARCReader, WARCRecord, iter_records

# response 记录中必需的核心头字段。
_REQUIRED_HEADERS = ("warc-type", "warc-record-id", "warc-date", "content-length")


@dataclass
class Issue:
    """一条审计问题。

    属性:
        severity: 严重级别，``error`` 或 ``warning``。
        code: 机器可读的问题代码，例如 ``digest_mismatch``。
        message: 人类可读描述。
        record_index: 记录序号（从 0 开始）。
        offset: 记录在归档中的字节偏移。
    """

    severity: str
    code: str
    message: str
    record_index: int
    offset: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "record_index": self.record_index,
            "offset": self.offset,
        }


@dataclass
class AuditReport:
    """审计汇总报告。"""

    total_records: int = 0
    valid_records: int = 0
    issues: List[Issue] = field(default_factory=list)
    checked_block_digests: int = 0
    checked_payload_digests: int = 0
    digests_ok: int = 0
    digests_failed: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def passed(self) -> bool:
        """当且仅当没有 error 级别问题时通过。"""
        return self.error_count == 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "checked_block_digests": self.checked_block_digests,
            "checked_payload_digests": self.checked_payload_digests,
            "digests_ok": self.digests_ok,
            "digests_failed": self.digests_failed,
            "issues": [i.to_dict() for i in self.issues],
        }


def _extract_http_payload(content: bytes) -> Optional[bytes]:
    """从 response 记录的内容块中提取 HTTP 正文（去掉状态行与头）。

    无法识别 HTTP 结构时返回 ``None``。使用 ``\\r\\n\\r\\n`` 或 ``\\n\\n``
    作为头/正文分隔符，兼容常见归档器。
    """
    header_end = content.find(b"\r\n\r\n")
    sep_len = 4
    if header_end == -1:
        header_end = content.find(b"\n\n")
        sep_len = 2
    if header_end == -1:
        return None
    return content[header_end + sep_len :]


def _audit_record(record: WARCRecord, index: int, report: AuditReport) -> None:
    """审计单条记录，将问题追加到报告并更新计数。"""
    offset = record.offset

    # 结构检查：解析阶段产生的告警。
    for warning in record.warnings:
        report.issues.append(
            Issue("error", "parse_warning", warning, index, offset)
        )

    # 必需头字段。
    for header in _REQUIRED_HEADERS:
        if not record.get(header):
            report.issues.append(
                Issue(
                    "error",
                    "missing_header",
                    f"缺少必需头字段: {header}",
                    index,
                    offset,
                )
            )

    # Content-Length 一致性。
    if record.content_length != record.actual_length:
        report.issues.append(
            Issue(
                "error",
                "length_mismatch",
                f"Content-Length={record.content_length} 与实际 "
                f"{record.actual_length} 字节不一致",
                index,
                offset,
            )
        )

    # 块摘要校验。
    block_digest = record.get("warc-block-digest")
    if block_digest:
        report.checked_block_digests += 1
        if verify_digest(record.content, block_digest):
            report.digests_ok += 1
        else:
            report.digests_failed += 1
            report.issues.append(
                Issue(
                    "error",
                    "digest_mismatch",
                    f"WARC-Block-Digest 校验失败: {block_digest}",
                    index,
                    offset,
                )
            )

    # 正文摘要校验（response 记录）。
    payload_digest = record.get("warc-payload-digest")
    if payload_digest and record.warc_type == "response":
        payload = _extract_http_payload(record.content)
        if payload is not None:
            report.checked_payload_digests += 1
            if verify_digest(payload, payload_digest):
                report.digests_ok += 1
            else:
                report.digests_failed += 1
                report.issues.append(
                    Issue(
                        "error",
                        "digest_mismatch",
                        f"WARC-Payload-Digest 校验失败: {payload_digest}",
                        index,
                        offset,
                    )
                )


def audit_reader(
    source: Union[str, os.PathLike, BinaryIO, WARCReader],
    *,
    strict: bool = False,
) -> AuditReport:
    """审计归档并返回 :class:`AuditReport`。

    参数:
        source: 路径、二进制流或 :class:`WARCReader` 实例。
        strict: 传递给解析器的严格模式开关。
    """
    report = AuditReport()
    if isinstance(source, WARCReader):
        records = iter(source)
    else:
        records = iter_records(source, strict=strict)

    for index, record in enumerate(records):
        report.total_records += 1
        _audit_record(record, index, report)
        if record.is_complete:
            report.valid_records += 1
    return report
