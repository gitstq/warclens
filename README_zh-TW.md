# WarcLens

> 零依賴 · 離線優先的 WARC 歸檔解析與完整性取證工具箱

[简体中文](README.md) · [繁體中文](README_zh-TW.md) · [English](README_en.md)

---

## 🎉 介紹

**WarcLens** 是一款以純 Python 標準庫打造的 WARC（ISO 28500，網頁歸檔格式）工具箱。它回答一個質樸卻關鍵的問題：**這份網頁歸檔，還完整嗎？**

歸檔檔案（`.warc` / `.warc.gz`）承載網站快照、網路取證樣本與長期保存資料。一旦在傳輸或儲存中損毀，往往無聲無息。WarcLens 以**串流、零依賴、確定性**的方式解析歸檔，逐筆校驗內容摘要，並輸出可機讀的取證報告，讓損毀無所遁形。

它既是可直接執行的命令列工具，也是能嵌入現有系統的 Python 函式庫——不連網、不裝包、不引入任何第三方執行期依賴。

## ✨ 特性

- 🧩 **零依賴**：僅用 Python 標準庫，裝好即用，無供應鏈風險。
- 🌀 **串流解析**：單遍掃描，記憶體用量與歸檔大小無關，GB 級歸檔也能處理。
- 🗜️ **透明解壓**：自動辨識 gzip 魔數，`.warc` 與 `.warc.gz` 一視同仁。
- 🔐 **完整性校驗**：重新計算並比對 `WARC-Block-Digest` / `WARC-Payload-Digest`（SHA-1 / SHA-256 / SHA-512 / MD5）。
- 🛡️ **優雅降級**：嚴格模式遇錯即停，寬鬆模式收集告警，損毀紀錄不會被悄悄吞掉。
- 🔍 **內容取證**：統計紀錄類型、URL、主機、HTTP 狀態、MIME，重建時間軸並辨識重複正文。
- 📊 **多格式報告**：JSON / CSV / Markdown 三種輸出，欄位穩定，便於流水線消費。
- 🔁 **雙介面**：命令列 `warclens` 與 Python `import warclens` 享有完全一致的能力。

## 🚀 快速開始

需要 Python 3.8 及以上，**無需安裝任何依賴**。

```bash
# 方式一：直接執行原始碼
python -m warclens version

# 方式二：安裝後使用指令（選擇性）
pip install .
warclens version
```

稽核一份歸檔是否完整：

```bash
warclens audit capture.warc.gz --format markdown
```

退出碼：`0` 表示通過（無 error），`1` 表示存在完整性問題，`2` 表示檔案或解析錯誤——便於接入 CI。

## 📖 使用指南

### 命令列

```bash
# 完整性稽核（結構 + 摘要），JSON 輸出
warclens audit capture.warc.gz -f json

# 內容統計：類型 / URL / 狀態 / MIME / 時間軸
warclens analyze capture.warc -f markdown

# 列出前 10 筆紀錄概要
warclens records capture.warc.gz --limit 10
```

### 作為函式庫使用

```python
from warclens import WARCReader, audit_reader, analyze_archive

# 1. 逐筆串流讀取（大型歸檔建議）
with WARCReader("capture.warc.gz") as reader:
    for record in reader:
        print(record.warc_type, record.warc_target_uri, record.actual_length)

# 2. 完整性稽核
report = audit_reader("capture.warc.gz")
if not report.passed:
    for issue in report.issues:
        print(issue.severity, issue.code, issue.message)

# 3. 內容分析
stats = analyze_archive("capture.warc.gz")
print(stats.type_counts, stats.status_counts, stats.duplicate_payloads)
```

### 摘要 API

```python
from warclens import encode_digest, verify_digest

digest = encode_digest(b"hello", "sha1")   # 'sha1:...'
assert verify_digest(b"hello", digest)
```

## 💡 設計迭代

本專案從真實歸檔工作流程的痛點出發，做了如下取捨：

| 關注點 | 設計決策 | 帶來的價值 |
| --- | --- | --- |
| 大檔案 | 單遍串流解析，不整體載入 | 記憶體恆定，可處理 GB 級歸檔 |
| 壓縮 | 魔數嗅探 + 透明 gzip | 呼叫方無須關心是否壓縮 |
| 損毀 | 嚴格/寬鬆雙模式 | 生產環境可容錯，CI 可卡關卡 |
| 摘要 | 演算法前綴 + Base32、大小寫不敏感 | 相容不同歸檔器的寫法差異 |
| 相容 | 支援 0.18 / 1.0 / 1.1 | 涵蓋歷史與現行歸檔 |
| 整合 | CLI 與函式庫共用核心 | 行為一致，易於自動化 |

## 📦 打包部署

```bash
# 執行測試 + 建置 sdist 與 wheel + 校驗產物，一條指令完成
./build.sh
```

產物位於 `dist/`：`warclens-1.0.0-py3-none-any.whl` 與 `warclens-1.0.0.tar.gz`，皆為純 Python、零依賴，可直接 `pip install`。

## 🤝 貢獻

歡迎貢獻！提交遵循 Angular 約定（如 `feat(parser): 支援新版本行`），新增功能請附單元測試並確保 `./build.sh` 通過。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 授權

本專案採用 [MIT 授權](LICENSE) 開源，可自由使用、修改與散佈。
