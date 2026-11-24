# WarcLens

> 零依赖 · 离线优先的 WARC 归档解析与完整性取证工具箱

[简体中文](README.md) · [繁體中文](README_zh-TW.md) · [English](README_en.md)

---

## 🎉 介绍

**WarcLens** 是一款用纯 Python 标准库打造的 WARC（ISO 28500，网页归档格式）工具箱。它回答一个朴素却关键的问题：**这份网页归档，还完整吗？**

归档文件（`.warc` / `.warc.gz`）承载着网站快照、网络取证样本与长期保存资料。一旦在传输或存储中损坏，往往静默无声。WarcLens 以**流式、零依赖、确定性**的方式解析归档，逐条校验内容摘要，并输出可机读的取证报告，让损坏无所遁形。

它既是一个可直接运行的命令行工具，也是可以嵌入现有系统的 Python 库——不联网、不装包、不引入任何第三方运行时依赖。

## ✨ 特性

- 🧩 **零依赖**：仅用 Python 标准库，装好即用，无供应链风险。
- 🌀 **流式解析**：单遍扫描，内存占用与归档大小无关， gigabyte 级归档也能处理。
- 🗜️ **透明解压**：自动识别 gzip 魔数，`.warc` 与 `.warc.gz` 一视同仁。
- 🔐 **完整性校验**：重新计算并比对 `WARC-Block-Digest` / `WARC-Payload-Digest`（SHA-1 / SHA-256 / SHA-512 / MD5）。
- 🛡️ **优雅降级**：严格模式遇错即停，宽松模式收集告警，损坏记录不会被悄悄吞掉。
- 🔍 **内容取证**：统计记录类型、URL、主机、HTTP 状态、MIME，重建时间线并识别重复正文。
- 📊 **多格式报告**：JSON / CSV / Markdown 三种输出，字段稳定，便于流水线消费。
- 🔁 **双接口**：命令行 `warclens` 与 Python `import warclens` 完全一致的能力。

## 🚀 快速开始

需要 Python 3.8 及以上，**无需安装任何依赖**。

```bash
# 方式一：直接运行源码
python -m warclens version

# 方式二：安装后使用命令（可选）
pip install .
warclens version
```

审计一份归档是否完整：

```bash
warclens audit capture.warc.gz --format markdown
```

退出码：`0` 表示通过（无 error），`1` 表示存在完整性问题，`2` 表示文件或解析错误——便于接入 CI。

## 📖 使用指南

### 命令行

```bash
# 完整性审计（结构 + 摘要），JSON 输出
warclens audit capture.warc.gz -f json

# 内容统计：类型 / URL / 状态 / MIME / 时间线
warclens analyze capture.warc -f markdown

# 列出前 10 条记录概要
warclens records capture.warc.gz --limit 10
```

### 作为库使用

```python
from warclens import WARCReader, audit_reader, analyze_archive

# 1. 逐条流式读取（大归档推荐）
with WARCReader("capture.warc.gz") as reader:
    for record in reader:
        print(record.warc_type, record.warc_target_uri, record.actual_length)

# 2. 完整性审计
report = audit_reader("capture.warc.gz")
if not report.passed:
    for issue in report.issues:
        print(issue.severity, issue.code, issue.message)

# 3. 内容分析
stats = analyze_archive("capture.warc.gz")
print(stats.type_counts, stats.status_counts, stats.duplicate_payloads)
```

### 摘要 API

```python
from warclens import encode_digest, verify_digest

digest = encode_digest(b"hello", "sha1")   # 'sha1:...'
assert verify_digest(b"hello", digest)
```

## 💡 设计迭代

本项目从真实归档工作流的痛点出发，做了如下取舍：

| 关注点 | 设计决策 | 带来的价值 |
| --- | --- | --- |
| 大文件 | 单遍流式解析，不整体载入 | 内存恒定，可处理 GB 级归档 |
| 压缩 | 魔数嗅探 + 透明 gzip | 调用方无需关心是否压缩 |
| 损坏 | 严格/宽松双模式 | 生产环境可容错，CI 可卡门禁 |
| 摘要 | 算法前缀 + Base32、大小写不敏感 | 兼容不同归档器的写法差异 |
| 兼容 | 支持 0.18 / 1.0 / 1.1 | 覆盖历史与现行归档 |
| 集成 | CLI 与库共用内核 | 行为一致，易于自动化 |

## 📦 打包部署

```bash
# 运行测试 + 构建 sdist 与 wheel + 校验产物，一条命令完成
./build.sh
```

产物位于 `dist/`：`warclens-1.0.0-py3-none-any.whl` 与 `warclens-1.0.0.tar.gz`，均为纯 Python、零依赖，可直接 `pip install`。

## 🤝 贡献

欢迎贡献！提交遵循 Angular 约定（如 `feat(parser): 支持新版本行`），新增功能请附单元测试并确保 `./build.sh` 通过。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 协议

本项目采用 [MIT 协议](LICENSE) 开源，可自由使用、修改与分发。
