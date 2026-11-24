"""WarcLens 命令行入口.

子命令：

* ``audit``  — 审计归档完整性（结构 + 摘要），输出 JSON/CSV/Markdown；
* ``analyze`` — 分析归档内容统计（类型/URL/状态/MIME/时间线）；
* ``records`` — 列出记录概要；
* ``version`` — 打印版本号。

示例::

    warclens audit capture.warc.gz --format markdown
    warclens analyze capture.warc --format json
    warclens records capture.warc.gz --limit 10
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, List, Optional, Sequence

from . import __version__
from .analyzer import AnalysisReport, analyze_archive
from .audit import AuditReport, audit_reader
from .parser import WARCParseError, WARCReader
from .report import to_csv, to_json, to_markdown

_FORMATS = ("json", "markdown", "csv")


def _render(data: Any, fmt: str, *, title: str = "WarcLens 报告") -> str:
    """按格式渲染数据。"""
    if fmt == "json":
        return to_json(data)
    if fmt == "markdown":
        return to_markdown(data, title=title)
    if fmt == "csv":
        plain = data.to_dict() if hasattr(data, "to_dict") else data
        if isinstance(plain, dict):
            rows = []
            for key, value in plain.items():
                if isinstance(value, (dict, list)):
                    continue
                rows.append({"metric": key, "value": value})
            return to_csv(rows, ["metric", "value"])
    return to_json(data)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="warclens",
        description="零依赖 WARC 归档解析与完整性取证工具箱",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"warclens {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("archive", help=".warc / .warc.gz 归档路径")
        sp.add_argument(
            "-f", "--format", choices=_FORMATS, default="json", help="输出格式"
        )
        sp.add_argument(
            "--strict", action="store_true", help="遇到损坏记录立即报错"
        )

    audit_sp = sub.add_parser("audit", help="审计归档完整性")
    add_common(audit_sp)

    analyze_sp = sub.add_parser("analyze", help="分析归档内容统计")
    add_common(analyze_sp)

    records_sp = sub.add_parser("records", help="列出记录概要")
    records_sp.add_argument("archive", help="归档路径")
    records_sp.add_argument("--limit", type=int, default=20, help="最多显示条数")
    records_sp.add_argument(
        "-f", "--format", choices=_FORMATS, default="json", help="输出格式"
    )
    records_sp.add_argument("--strict", action="store_true", help="严格模式")

    sub.add_parser("version", help="打印版本号")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行主函数，返回进程退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "version"):
        if args.command is None:
            parser.print_help()
        else:
            print(__version__)
        return 0

    try:
        if args.command == "audit":
            report = audit_reader(args.archive, strict=args.strict)
            sys.stdout.write(_render(report, args.format, title="WarcLens 完整性审计报告"))
            return 0 if report.passed else 1

        if args.command == "analyze":
            report = analyze_archive(args.archive, strict=args.strict)
            sys.stdout.write(_render(report, args.format, title="WarcLens 内容分析报告"))
            return 0

        if args.command == "records":
            rows: List[dict] = []
            with WARCReader(args.archive, strict=args.strict) as reader:
                for index, record in enumerate(reader):
                    if index >= args.limit:
                        break
                    rows.append(
                        {
                            "index": index,
                            "type": record.warc_type,
                            "uri": record.warc_target_uri,
                            "date": record.warc_date,
                            "bytes": record.actual_length,
                            "offset": record.offset,
                        }
                    )
            if args.format == "csv":
                sys.stdout.write(
                    to_csv(
                        rows, ["index", "type", "uri", "date", "bytes", "offset"]
                    )
                )
            else:
                sys.stdout.write(to_json(rows))
            return 0
    except WARCParseError as exc:
        sys.stderr.write(f"解析失败: {exc}\n")
        return 2
    except FileNotFoundError:
        sys.stderr.write(f"文件不存在: {args.archive}\n")
        return 2
    except OSError as exc:
        sys.stderr.write(f"IO 错误: {exc}\n")
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
