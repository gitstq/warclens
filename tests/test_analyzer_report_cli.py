"""分析、报告与 CLI 的集成单元测试。"""

from __future__ import annotations

import io
import json
import tempfile
import os
import unittest

from warclens import __version__
from warclens.analyzer import analyze_archive
from warclens.audit import audit_reader
from warclens.cli import main
from warclens.digest import encode_digest
from warclens.report import to_csv, to_json, to_markdown

from _fixtures import make_archive, make_http_response, make_record


def _sample_archive() -> bytes:
    r1 = make_record("warcinfo", b"software: test\r\n", add_block_digest=False)
    body = b"<h1>Hello</h1>"
    content = make_http_response(body)
    r2 = make_record(
        "response",
        content,
        uri="http://example.com/a",
        date="2024-01-02T00:00:00Z",
        add_payload_digest=True,
        payload_digest=encode_digest(body, "sha1"),
    )
    r3 = make_record(
        "response",
        content,
        uri="http://example.com/b",
        date="2024-01-01T00:00:00Z",
        add_payload_digest=True,
        payload_digest=encode_digest(body, "sha1"),
    )
    return make_archive([r1, r2, r3])


class TestAnalyzer(unittest.TestCase):
    def test_analysis_counts(self):
        report = analyze_archive(io.BytesIO(_sample_archive()))
        self.assertEqual(report.total_records, 3)
        self.assertEqual(report.type_counts["response"], 2)
        self.assertEqual(report.type_counts["warcinfo"], 1)
        self.assertEqual(report.unique_urls, 2)
        self.assertEqual(report.unique_hosts, 1)
        self.assertEqual(report.status_counts["200"], 2)
        self.assertEqual(report.mime_counts["text/html"], 2)
        self.assertEqual(report.duplicate_payloads, 1)
        self.assertEqual(report.earliest_date, "2024-01-01T00:00:00Z")
        self.assertEqual(report.latest_date, "2024-01-02T00:00:00Z")


class TestReport(unittest.TestCase):
    def test_to_json_valid(self):
        report = audit_reader(io.BytesIO(_sample_archive()))
        data = json.loads(to_json(report))
        self.assertIn("passed", data)

    def test_to_markdown(self):
        report = audit_reader(io.BytesIO(_sample_archive()))
        md = to_markdown(report, title="测试")
        self.assertTrue(md.startswith("# 测试"))
        self.assertIn("total_records", md)

    def test_to_csv(self):
        csv = to_csv([{"a": 1, "b": 2}], ["a", "b"])
        self.assertIn("a,b", csv)
        self.assertIn("1,2", csv)


class TestCLI(unittest.TestCase):
    def setUp(self):
        fh = tempfile.NamedTemporaryFile(suffix=".warc", delete=False)
        fh.write(_sample_archive())
        fh.close()
        self.path = fh.name

    def tearDown(self):
        os.unlink(self.path)

    def test_version(self):
        self.assertEqual(main(["version"]), 0)

    def test_audit_command(self):
        self.assertEqual(main(["audit", self.path, "-f", "json"]), 0)

    def test_analyze_command(self):
        self.assertEqual(main(["analyze", self.path, "-f", "markdown"]), 0)

    def test_records_command(self):
        self.assertEqual(main(["records", self.path, "--limit", "2"]), 0)

    def test_missing_file(self):
        self.assertEqual(main(["audit", "/nonexistent/path.warc"]), 2)


if __name__ == "__main__":
    unittest.main()
