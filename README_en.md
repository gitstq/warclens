# WarcLens

> A dependency-free, offline-first toolkit for WARC archive parsing and integrity forensics

[简体中文](README.md) · [繁體中文](README_zh-TW.md) · [English](README_en.md)

---

## 🎉 Introduction

**WarcLens** is a WARC (ISO 28500, the web archive format) toolkit built entirely on the Python standard library. It answers a simple but critical question: **is this web archive still intact?**

WARC files (`.warc` / `.warc.gz`) hold website snapshots, network-forensics captures, and long-term preservation material. Corruption introduced during transfer or storage is usually silent. WarcLens parses archives in a **streaming, dependency-free, deterministic** fashion, verifies content digests record by record, and emits machine-readable forensic reports—so damage cannot hide.

It works both as a ready-to-run command-line tool and as a Python library you can embed in existing systems: no network calls, no package installs, no third-party runtime dependencies whatsoever.

## ✨ Features

- 🧩 **Zero dependencies**: standard library only—install and go, with no supply-chain risk.
- 🌀 **Streaming parser**: single-pass scanning whose memory use is independent of archive size; multi-gigabyte archives are fine.
- 🗜️ **Transparent decompression**: sniffs the gzip magic bytes; `.warc` and `.warc.gz` are treated alike.
- 🔐 **Integrity checks**: recomputes and compares `WARC-Block-Digest` / `WARC-Payload-Digest` (SHA-1 / SHA-256 / SHA-512 / MD5).
- 🛡️ **Graceful degradation**: strict mode fails fast; lenient mode collects warnings—damaged records are never silently swallowed.
- 🔍 **Content forensics**: tallies record types, URLs, hosts, HTTP statuses and MIME types, rebuilds timelines, and flags duplicate payloads.
- 📊 **Multiple report formats**: JSON / CSV / Markdown with stable fields, ready for pipeline consumption.
- 🔁 **Dual interface**: the `warclens` CLI and `import warclens` share the exact same core.

## 🚀 Quick Start

Python 3.8+ is required; **no dependencies to install**.

```bash
# Option 1: run straight from source
python -m warclens version

# Option 2: install, then use the command (optional)
pip install .
warclens version
```

Audit whether an archive is intact:

```bash
warclens audit capture.warc.gz --format markdown
```

Exit codes: `0` = passed (no errors), `1` = integrity problems found, `2` = file or parse error—handy for CI gating.

## 📖 Usage Guide

### Command line

```bash
# Integrity audit (structure + digests), JSON output
warclens audit capture.warc.gz -f json

# Content statistics: types / URLs / statuses / MIME / timeline
warclens analyze capture.warc -f markdown

# List the first 10 record summaries
warclens records capture.warc.gz --limit 10
```

### As a library

```python
from warclens import WARCReader, audit_reader, analyze_archive

# 1. Stream records one by one (recommended for large archives)
with WARCReader("capture.warc.gz") as reader:
    for record in reader:
        print(record.warc_type, record.warc_target_uri, record.actual_length)

# 2. Integrity audit
report = audit_reader("capture.warc.gz")
if not report.passed:
    for issue in report.issues:
        print(issue.severity, issue.code, issue.message)

# 3. Content analysis
stats = analyze_archive("capture.warc.gz")
print(stats.type_counts, stats.status_counts, stats.duplicate_payloads)
```

### Digest API

```python
from warclens import encode_digest, verify_digest

digest = encode_digest(b"hello", "sha1")   # 'sha1:...'
assert verify_digest(b"hello", digest)
```

## 💡 Design & Iteration

WarcLens was shaped by real pain points in archive workflows:

| Concern | Design decision | Benefit |
| --- | --- | --- |
| Large files | Single-pass streaming, never load whole archive | Constant memory; GB-scale support |
| Compression | Magic-byte sniffing + transparent gzip | Callers need not care about compression |
| Corruption | Strict and lenient modes | Production can tolerate; CI can gate |
| Digests | Algorithm prefix + Base32, case-insensitive | Tolerates writer-specific spellings |
| Compatibility | 0.18 / 1.0 / 1.1 support | Covers historical and current archives |
| Integration | CLI and library share one core | Consistent behavior, easy automation |

## 📦 Packaging & Deployment

```bash
# Run tests + build sdist and wheel + verify artifacts, all in one command
./build.sh
```

Artifacts land in `dist/`: `warclens-1.0.0-py3-none-any.whl` and `warclens-1.0.0.tar.gz`, both pure Python and dependency-free, ready to `pip install`.

## 🤝 Contributing

Contributions are welcome! Follow the Angular commit convention (e.g. `feat(parser): support new version line`), add unit tests for new features, and make sure `./build.sh` passes. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

Released under the [MIT License](LICENSE)—free to use, modify, and distribute.
