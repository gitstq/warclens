"""报告序列化.

将分析结果与审计报告渲染为 JSON / CSV / Markdown，输出为字符串，
调用方可自由写入文件或终端。全部使用标准库，输出确定性（字段顺序固定）。
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List


def _to_plain(obj: Any) -> Any:
    """递归将 dataclass / 列表 / 字典转换为可 JSON 序列化的普通结构。"""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def to_json(data: Any, *, indent: int = 2) -> str:
    """将数据序列化为格式化 JSON 字符串。"""
    return json.dumps(
        _to_plain(data), ensure_ascii=False, indent=indent, sort_keys=False
    ) + "\n"


def to_csv(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    """将字典列表渲染为 CSV 字符串。

    参数:
        rows: 每行一个字典。
        columns: 输出的列名，同时作为表头与取值键。
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _to_plain(row.get(col, "")) for col in columns})
    return buf.getvalue()


def to_markdown(data: Any, *, title: str = "WarcLens 报告") -> str:
    """将字典/审计结果渲染为简洁的 Markdown 报告。"""
    plain = _to_plain(data)
    lines: List[str] = [f"# {title}", ""]

    if isinstance(plain, dict):
        lines.append("| 指标 | 值 |")
        lines.append("| --- | --- |")
        for key, value in plain.items():
            if isinstance(value, (list, dict)):
                display = f"{len(value)} 项"
            else:
                display = str(value)
            lines.append(f"| `{key}` | {display} |")
        lines.append("")

        issues = plain.get("issues")
        if isinstance(issues, list) and issues:
            lines.append("## 问题明细")
            lines.append("")
            lines.append("| 级别 | 代码 | 记录 | 说明 |")
            lines.append("| --- | --- | --- | --- |")
            for issue in issues:
                if isinstance(issue, dict):
                    lines.append(
                        "| {severity} | {code} | {idx} | {msg} |".format(
                            severity=issue.get("severity", ""),
                            code=issue.get("code", ""),
                            idx=issue.get("record_index", ""),
                            msg=str(issue.get("message", "")).replace("|", "\\|"),
                        )
                    )
            lines.append("")
    elif isinstance(plain, list):
        for item in plain:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)
