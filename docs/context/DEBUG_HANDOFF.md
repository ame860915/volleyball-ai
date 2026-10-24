# DEBUG_HANDOFF

Review Brief 與錯誤交接紀錄。新紀錄加在最上方。

---

## Review Brief 範本

```markdown
### [Task ID] 標題 — YYYY-MM-DD

- **Requirement**：對應 REQUIREMENTS.md 的編號
- **Branch / Commit**：
- **Changed Files**：
- **Diff Summary**：
- **Environment**：volleyball conda、Python x.y、FFmpeg 9.0.2
- **Reproduction Steps**：
- **Executed Tests**：指令
- **Test Results**：實際輸出（通過 / 失敗數）
- **Known Issues**：
- **Review Questions**：希望 Codex 特別檢查的地方

#### Codex 回報
（貼上 Codex 結果）

#### 處理結果
（修正內容與 commit）
```

---

## 錯誤紀錄範本

```markdown
### BUG-### 標題 — YYYY-MM-DD

- **現象**：
- **重現步驟**：
- **預期 / 實際**：
- **原因**：
- **修正**：
- **回歸測試**：
```

---

### [2.1] vball clip — 2026-10-22

- **Requirement**：REQUIREMENTS.md R0.2–R0.6
- **Branch / Commit**：main（待填）
- **Changed Files**：`src/vball/video/clip.py`（新）、`src/vball/errors.py`（新增 ClipError）、`src/vball/cli.py`（新增 clip 子指令）、`tests/test_clip.py`（新）
- **Diff Summary**：`clip_video()` 依序 probe 輸入 → 驗證時間範圍 → 驗證輸出（不可等於輸入、不可為資料夾、預設不覆蓋、寫入測試）→ FFmpeg 寫入 `.tmp.mp4` → 量測輸出 video stream 長度 → copy 模式以 ffprobe packet flags 找起點前 Keyframe → 計算誤差與 warning → `os.replace` 改名 → 寫 `.json` 與 `.log`。失敗時 finally 刪除 `.tmp.mp4`。
- **Environment**：volleyball conda、Python 3.13.13、FFmpeg 9.0.2（Windows）
- **Reproduction Steps**：`vball clip tests/fixtures/videos/cfr30_audio.mp4 --start-ms 1500 --end-ms 2500 --out outputs/copy.mp4 --mode copy`
- **Executed Tests**：`pytest -q`；設定 VBALL_REAL_VIDEO 後再跑一次
- **Test Results**：Linux 94 passed, 3 skipped；Windows 待填
- **Known Issues**：
  - copy 模式 Keyframe 只往前找 60 秒；GOP 更長的影片會回報 actual_start = null
  - accurate 模式容許值以 fps_avg 計算，VFR 影片僅供參考
  - 重新編碼固定 libx264 veryfast / crf 18，未使用 NVENC
  - 無效 mode 在 Python API 回報 INVALID_RANGE（CLI 由 argparse 先擋下）
- **Review Questions**：
  1. copy 模式「實際起點 = 起點前最近 Keyframe」的推算，在 B-frame、open GOP 或 edit list 的手機影片是否會錯？
  2. `-ss` 放在 `-i` 前（input seeking）搭配重新編碼，是否在所有情況都 frame-accurate？
  3. Windows 上 `os.replace` 遇到目標檔被播放器開啟時的行為與錯誤代碼是否合理？
  4. 是否有 FFmpeg 成功但輸出不完整、卻通過驗證的情況？

#### Codex 回報
（待貼上）

#### 處理結果
（待填）

---

### [1.5] vball probe — 2026-10-20

- **Requirement**：REQUIREMENTS.md R0.1
- **Branch / Commit**：main（待填）
- **Changed Files**：`src/vball/errors.py`（新）、`src/vball/video/__init__.py`（新）、`src/vball/video/probe.py`（新）、`src/vball/cli.py`（新增 probe 子指令與錯誤處理）、`tests/conftest.py`（新）、`tests/test_probe.py`（新）
- **Diff Summary**：以 ffprobe JSON 解析 VideoMetadata；檔案不存在 / 0 位元組 / 無 video stream / duration ≤ 0 皆拋出帶代碼的 ProbeError；r 與 avg frame rate 相差 > 1% 標記 is_vfr_suspected；CLI 成功輸出 JSON（exit 0），錯誤輸出 `ERROR [CODE] 訊息` 到 stderr（exit 1）
- **Environment**：volleyball conda、Python 3.13.13、FFmpeg 9.0.2（Windows）
- **Reproduction Steps**：`python tests/fixtures/make_fixtures.py`；`vball probe tests/fixtures/videos/vfr_mixed.mp4`
- **Executed Tests**：`pytest -q`；`$env:VBALL_REAL_VIDEO=...; pytest -q -m real_video`
- **Test Results**：Windows 實測 `pytest -q` 25 passed（含 `20260719.mp4`）；真實影片 r 30/1、avg 29.823（差 0.6%），判定非 VFR
- **Known Issues**：fps_avg 僅供參考；VFR 判斷門檻 1% 為初始值，未經大量真實影片驗證
- **Review Questions**：
  1. VFR 判斷（r vs avg 相差 1%）對手機影片是否過於敏感或遲鈍？
  2. Windows 中文路徑、空白路徑、cp950 主控台輸出是否有問題？
  3. ffprobe 回傳成功但 streams 欄位異常（如 width 缺失）時，是否應改為 INVALID_VIDEO？

#### Codex 回報（2026-10-20，摘要）

| # | Severity | 問題 | 重現 |
|---|---|---|---|
| 1 | Medium | 異常 metadata 未統一轉為 INVALID_VIDEO | width 缺失回傳 0；width / streams 為 null 拋出 TypeError；CLI 出現 traceback |
| 2 | Medium | cp950 stdout 無法輸出部分合法路徑 | 路徑含 🏐 時 UnicodeEncodeError |
| 3 | Medium | duration 異常值 | "inf" → OverflowError；"0.0001" → duration_ms = 0 |
| 4 | Medium | ffprobe 啟動失敗未轉為 ProbeError | PermissionError 直接拋出 |
| 5 | Low | VFR 無法表達「資訊不足」；無法偵測局部間隔變化 | rate 缺失時回傳 false |
| 6 | Medium | 測試不足以證明 R0.1 | 真實影片只檢查 duration 與解析度 |

Review Questions 回覆：Q1 1% 門檻目前證據不足，需更多已知時間戳樣本；Q2 參數 list + UTF-8 解碼合理，但輸出端需處理 cp950；Q3 缺少解析度應判定 INVALID_VIDEO。

#### 處理結果（2026-10-20）

| # | 處理 | 說明 |
|---|---|---|
| 1 | 已修正 | 新增 `_parse()`：驗證頂層、streams、format、stream 型別；width / height 須為正整數 |
| 2 | 已修正 | stdout 先輸出可讀 JSON，編碼失敗改為 `ensure_ascii=True`（仍為有效 JSON）；stderr 設 `errors="replace"` |
| 3 | 已修正 | `math.isfinite` 檢查，毫秒值須 > 0，否則嘗試下一來源 |
| 4 | 已修正 | FileNotFoundError → FFPROBE_NOT_FOUND；其他 OSError → FFPROBE_FAILED，保留 exception chaining |
| 5 | 部分修正 | rate 資訊不足時 `is_vfr_suspected = null`；局部時間戳分析延到 W3 |
| 6 | 已修正 | 新增 `tests/test_probe_edge.py`（mock 異常 schema、啟動失敗、VFR 門檻上下界、cp950 串流）；CLI 完整 JSON 比對、子程序 exit code 與 stdout / stderr 分離；真實影片比對全部 R0.1 欄位 |

驗證：舊版程式在 mock 下重現 #1、#3 共 5 個問題；修正後 `pytest -q` 67 passed, 1 skipped（Linux，Python 3.13）；Windows 實測 68 passed（含真實影片，2026-10-21）。**Review 結案。**
