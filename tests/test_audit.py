"""审计模块单元测试。"""

from __future__ import annotations

import io
import unittest

from warclens.audit import audit_reader
from warclens.digest import encode_digest

from _fixtures import make_archive, make_http_response, make_record


class TestAudit(unittest.TestCase):
    def test_valid_archive_passes(self):
        body = b"<html>ok</html>"
        content = make_http_response(body)
        rec = make_record(
            "response",
            content,
            uri="http://example.com/",
            add_block_digest=True,
            add_payload_digest=True,
            payload_digest=encode_digest(body, "sha1"),
        )
        report = audit_reader(io.BytesIO(make_archive([rec])))
        self.assertTrue(report.passed)
        self.assertEqual(report.total_records, 1)
        self.assertEqual(report.valid_records, 1)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.checked_block_digests, 1)
        self.assertEqual(report.checked_payload_digests, 1)
        self.assertEqual(report.digests_ok, 2)

    def test_block_digest_mismatch_detected(self):
        content = make_http_response(b"body")
        rec = make_record("response", content, add_block_digest=True)
        # 篡改内容但保留原摘要头。
        tampered = rec.replace(b"body", b"BODY")
        # 注意：替换后 Content-Length 不变（等长），摘要会失配。
        report = audit_reader(io.BytesIO(make_archive([tampered])))
        self.assertFalse(report.passed)
        self.assertGreaterEqual(report.digests_failed, 1)
        codes = [i.code for i in report.issues]
        self.assertIn("digest_mismatch", codes)

    def test_missing_required_header(self):
        # 手工构造缺少 WARC-Date 的记录。
        content = b"x"
        head = (
            b"WARC/1.0\r\nWARC-Type: resource\r\n"
            b"WARC-Record-ID: <urn:uuid:2>\r\n"
            b"Content-Length: " + str(len(content)).encode() + b"\r\n"
            b"Content-Type: application/octet-stream\r\n\r\n"
        )
        report = audit_reader(io.BytesIO(head + content + b"\r\n\r\n"))
        self.assertFalse(report.passed)
        codes = [i.code for i in report.issues]
        self.assertIn("missing_header", codes)

    def test_payload_digest_mismatch(self):
        content = make_http_response(b"real body")
        rec = make_record(
            "response",
            content,
            add_payload_digest=True,
            payload_digest=encode_digest(b"WRONG BODY", "sha1"),
        )
        report = audit_reader(io.BytesIO(make_archive([rec])))
        self.assertFalse(report.passed)
        self.assertIn(
            "digest_mismatch", [i.code for i in report.issues]
        )

    def test_length_mismatch(self):
        head = (
            b"WARC/1.0\r\nWARC-Type: resource\r\n"
            b"WARC-Record-ID: <urn:uuid:3>\r\nWARC-Date: 2024-01-01T00:00:00Z\r\n"
            b"Content-Length: 20\r\nContent-Type: application/octet-stream\r\n\r\n"
        )
        report = audit_reader(io.BytesIO(head + b"short\r\n\r\n"))
        self.assertFalse(report.passed)
        self.assertIn("length_mismatch", [i.code for i in report.issues])

    def test_empty_archive(self):
        report = audit_reader(io.BytesIO(b""))
        self.assertTrue(report.passed)
        self.assertEqual(report.total_records, 0)

    def test_report_to_dict(self):
        rec = make_record("resource", b"x", add_block_digest=False)
        report = audit_reader(io.BytesIO(make_archive([rec])))
        data = report.to_dict()
        self.assertIn("passed", data)
        self.assertIn("issues", data)
        self.assertIsInstance(data["issues"], list)


if __name__ == "__main__":
    unittest.main()
