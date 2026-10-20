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

### [1.5] vball probe — 2026-10-20

- **Requirement**：REQUIREMENTS.md R0.1
- **Branch / Commit**：main（待填）
- **Changed Files**：`src/vball/errors.py`（新）、`src/vball/video/__init__.py`（新）、`src/vball/video/probe.py`（新）、`src/vball/cli.py`（新增 probe 子指令與錯誤處理）、`tests/conftest.py`（新）、`tests/test_probe.py`（新）
- **Diff Summary**：以 ffprobe JSON 解析 VideoMetadata；檔案不存在 / 0 位元組 / 無 video stream / duration ≤ 0 皆拋出帶代碼的 ProbeError；r 與 avg frame rate 相差 > 1% 標記 is_vfr_suspected；CLI 成功輸出 JSON（exit 0），錯誤輸出 `ERROR [CODE] 訊息` 到 stderr（exit 1）
- **Environment**：volleyball conda、Python 3.13.13、FFmpeg 9.0.2（Windows）
- **Reproduction Steps**：`python tests/fixtures/make_fixtures.py`；`vball probe tests/fixtures/videos/vfr_mixed.mp4`
- **Executed Tests**：`pytest -q`；`$env:VBALL_REAL_VIDEO=...; pytest -q -m real_video`
- **Test Results**：（待 Windows 實測填入）
- **Known Issues**：fps_avg 僅供參考；VFR 判斷門檻 1% 為初始值，未經大量真實影片驗證
- **Review Questions**：
  1. VFR 判斷（r vs avg 相差 1%）對手機影片是否過於敏感或遲鈍？
  2. Windows 中文路徑、空白路徑、cp950 主控台輸出是否有問題？
  3. ffprobe 回傳成功但 streams 欄位異常（如 width 缺失）時，是否應改為 INVALID_VIDEO？

#### Codex 回報
（待貼上）

#### 處理結果
（待填）
