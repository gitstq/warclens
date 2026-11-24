"""解析器单元测试。"""

from __future__ import annotations

import gzip
import io
import os
import tempfile
import unittest

from warclens.parser import WARCParseError, WARCReader, iter_records
from warclens.digest import encode_digest

from _fixtures import make_archive, make_http_response, make_record


class TestParser(unittest.TestCase):
    def test_parse_basic_record(self):
        rec = make_record("warcinfo", b"software: WarcLens\r\n", add_block_digest=False)
        records = list(iter_records(io.BytesIO(make_archive([rec]))))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].version, "WARC/1.0")
        self.assertEqual(records[0].warc_type, "warcinfo")
        self.assertEqual(records[0].content, b"software: WarcLens\r\n")
        self.assertEqual(records[0].content_length, len(records[0].content))
        self.assertTrue(records[0].is_complete)

    def test_multiple_records(self):
        r1 = make_record("warcinfo", b"x\r\n", add_block_digest=False)
        r2 = make_record(
            "response",
            make_http_response(b"hello"),
            uri="http://example.com/",
            add_block_digest=True,
        )
        records = list(iter_records(io.BytesIO(make_archive([r1, r2]))))
        self.assertEqual(len(records), 2)
        self.assertEqual([r.warc_type for r in records], ["warcinfo", "response"])
        self.assertEqual(records[1].warc_target_uri, "http://example.com/")

    def test_gzip_transparent(self):
        rec = make_record("resource", b"payload", uri="http://x.test/a")
        blob = make_archive([rec], gzipped=True)
        self.assertTrue(blob.startswith(b"\x1f\x8b"))
        with tempfile.NamedTemporaryFile(suffix=".warc.gz", delete=False) as fh:
            fh.write(blob)
            path = fh.name
        try:
            records = WARCReader(path).read_all()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].content, b"payload")
        finally:
            os.unlink(path)

    def test_header_case_insensitive(self):
        rec = make_record("resource", b"p", add_block_digest=False)
        records = list(iter_records(io.BytesIO(make_archive([rec]))))
        self.assertEqual(records[0].get("WARC-TYPE"), "resource")
        self.assertEqual(records[0].get("Content-Length"), "1")

    def test_versions_supported(self):
        for version in ("WARC/0.18", "WARC/1.0", "WARC/1.1"):
            with self.subTest(version=version):
                rec = make_record("resource", b"p", version=version, add_block_digest=False)
                records = list(iter_records(io.BytesIO(make_archive([rec]))))
                self.assertEqual(records[0].version, version)
                self.assertNotIn("不支持", "".join(records[0].warnings))

    def test_truncated_content_lenient(self):
        # 声明长度大于实际内容：宽松模式应记录告警而非抛错。
        head = (
            b"WARC/1.0\r\nWARC-Type: resource\r\n"
            b"WARC-Record-ID: <urn:uuid:1>\r\nWARC-Date: 2024-01-01T00:00:00Z\r\n"
            b"Content-Length: 100\r\nContent-Type: application/octet-stream\r\n\r\n"
        )
        blob = head + b"short\r\n\r\n"
        records = list(iter_records(io.BytesIO(blob), strict=False))
        self.assertEqual(len(records), 1)
        # read(100) 会读走流中剩余的全部 9 字节（short + CRLF CRLF）。
        self.assertEqual(records[0].actual_length, 9)
        self.assertFalse(records[0].is_complete)
        self.assertTrue(any("截断" in w for w in records[0].warnings))

    def test_truncated_content_strict(self):
        head = (
            b"WARC/1.0\r\nWARC-Type: resource\r\n"
            b"WARC-Record-ID: <urn:uuid:1>\r\nWARC-Date: 2024-01-01T00:00:00Z\r\n"
            b"Content-Length: 100\r\nContent-Type: application/octet-stream\r\n\r\n"
        )
        blob = head + b"short\r\n\r\n"
        with self.assertRaises(WARCParseError):
            list(iter_records(io.BytesIO(blob), strict=True))

    def test_empty_archive(self):
        self.assertEqual(list(iter_records(io.BytesIO(b""))), [])

    def test_context_manager(self):
        rec = make_record("resource", b"data", add_block_digest=False)
        blob = make_archive([rec])
        with tempfile.NamedTemporaryFile(suffix=".warc", delete=False) as fh:
            fh.write(blob)
            path = fh.name
        try:
            with WARCReader(path) as reader:
                count = sum(1 for _ in reader)
            self.assertEqual(count, 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
