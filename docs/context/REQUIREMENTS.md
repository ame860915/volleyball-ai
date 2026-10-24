# REQUIREMENTS

## 功能分級

| 等級 | 功能 | 版本 |
|---|---|---|
| **Must** | 影片 metadata、手動切片（copy / accurate）、切片 JSON 與 log | V0 |
| **Must** | 上傳、Rally 時間軸（手動標記 + 人工修正）、Highlight 合成、報告 v1 | V1 |
| **Should** | 規則式 Rally 候選、Player Detection / Tracking、Pose 候選 | V1（不得阻擋 Must） |
| **Should** | Ball Detection / Tracking、Touch 候選、Court Homography、落點 In/Out/Uncertain | V2 |
| **Should** | Action Recognition、球員統計、Highlight Ranking | V2 |
| **Later** | 半自動計分、失誤原因、改善建議、戰術分析 | V3 |
| **Later** | 已驗證真實球速、多機位、Mobile App、商業訂閱 | V3 |

## V0 驗收：影片切片

| # | 需求 | 驗收 |
|---|---|---|
| R0.1 | `vball probe` 讀取 duration、fps（r / avg）、解析度、codec、是否有音訊 | 對合成 fixture 與 `20260719.mp4` 輸出正確 JSON |
| R0.2 | `vball clip` 支援 `--mode copy` 與 `--mode accurate` | 兩種模式皆輸出可播放 MP4 |
| R0.3 | 時間驗證：`0 ≤ start < end ≤ duration` | 違反時拋出 `ClipError` 並帶錯誤代碼 |
| R0.4 | 輸出先寫 `.tmp` 再 rename；預設不覆蓋 | 已存在且無 `--overwrite` → `OUTPUT_EXISTS` |
| R0.5 | JSON 同時記錄 requested 與 actual 起訖時間 | copy 模式不宣稱 Frame-accurate |
| R0.6 | 每次執行寫 log | log 含輸入、參數、FFmpeg 指令、耗時、結果 |

錯誤代碼：`INPUT_NOT_FOUND`、`INVALID_VIDEO`、`INVALID_RANGE`、`OUTPUT_EXISTS`、`OUTPUT_NOT_WRITABLE`、`FFMPEG_NOT_FOUND`、`FFMPEG_FAILED`、`FFPROBE_NOT_FOUND`、`FFPROBE_FAILED`。

metadata 必要欄位（video stream、正整數解析度、有限且 > 0 的 duration）缺失或異常，一律為 `INVALID_VIDEO`。

## V1 驗收：MVP

上傳 → Rally 時間軸 → 人工修正 → Highlight MP4 → 報告，可用一支完整比賽影片端到端跑通。

## 共通規則

- 無法判斷的結果輸出 `unknown` / `uncertain`。
- 速度單位明確標示 `pixel` / `projected` / `true`；`true` 需校正與 Ground Truth 驗證。
- 計分不得只憑最後觸球人判定失誤原因。
