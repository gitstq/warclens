"""摘要编解码与校验单元测试。"""

from __future__ import annotations

import unittest

from warclens.digest import (
    compute_block_digest,
    encode_digest,
    normalize_digest_header,
    parse_digest,
    verify_digest,
)


class TestDigest(unittest.TestCase):
    def test_encode_empty_sha1(self):
        # 空串的 SHA-1 base32 是已知常量。
        value = encode_digest(b"", "sha1")
        self.assertEqual(value, "sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ")

    def test_encode_various_algorithms(self):
        for algo in ("sha1", "sha256", "sha512", "md5"):
            with self.subTest(algo=algo):
                value = encode_digest(b"warc", algo)
                self.assertTrue(value.startswith(f"{algo}:"))
                self.assertTrue(verify_digest(b"warc", value))

    def test_verify_case_insensitive(self):
        value = encode_digest(b"content", "sha1")
        self.assertTrue(verify_digest(b"content", value.lower()))
        self.assertTrue(verify_digest(b"content", value.upper()))

    def test_verify_mismatch(self):
        value = encode_digest(b"content", "sha1")
        self.assertFalse(verify_digest(b"different", value))

    def test_verify_invalid_string(self):
        self.assertFalse(verify_digest(b"content", "not-a-digest"))
        self.assertFalse(verify_digest(b"content", "foo:ABCDEF"))
        self.assertFalse(verify_digest(b"content", ""))

    def test_parse_digest(self):
        self.assertEqual(parse_digest("sha1:ABC"), ("sha1", "ABC"))
        self.assertEqual(parse_digest("SHA-256:abc="), ("sha256", "ABC"))
        self.assertIsNone(parse_digest("garbage"))

    def test_normalize_digest_header(self):
        self.assertEqual(normalize_digest_header("sha1:abc"), "sha1:ABC")
        self.assertEqual(normalize_digest_header("weird"), "weird")

    def test_compute_block_digest(self):
        self.assertEqual(compute_block_digest(b"x"), encode_digest(b"x", "sha1"))

    def test_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            encode_digest(b"x", "sha999")


if __name__ == "__main__":
    unittest.main()
