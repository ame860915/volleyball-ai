# TEST_RESULTS

只記錄**實際執行過**的結果。新紀錄加在最上方。

| 日期 | Task | 指令 | 結果 | 備註 |
|---|---|---|---|---|
| 2026-10-25 | 2.1 修正 | 人工播放 `fix_accurate.mp4`、`fix_copy.mp4` | 使用者回報完成，未回報異常 | 輸出 video 晚於 audio 開始：accurate 0.033 s、copy 0.094 s |
| 2026-10-25 | 2.1 修正 | 真實影片 `--mode copy` 1000–4000 | actual 998–4066，start_basis measured，起點誤差 2 ms、終點 66 ms，status warning；MAD best 0.00 / second 1.17 | Windows；998.333 ms 為 Keyframe（ffprobe 核對） |
| 2026-10-25 | 2.1 修正 | 真實影片 accurate 1000–4000 | actual 1032–3999，start_basis measured，起點誤差 32 ms（容許 50）、終點 1 ms，frame_accurate true；MAD best 0.35 / second 1.27 | Windows；1000 ms 後第一格為 1031.667 ms（ffprobe 核對） |
| 2026-10-25 | 2.1 修正 | `pytest -q`（設定 VBALL_REAL_VIDEO，Windows） | 118 passed in 24.35s | 修正 `test_start_time_offset` 寫死期望值後 |
| 2026-10-25 | 2.1 修正 | `pytest -q`（設定 VBALL_REAL_VIDEO，Windows） | 117 passed, 1 failed in 31.56s | `test_start_time_offset` 期望 1022，實際 1021（start_time 0.478667，1021.333 → 1021）；測試寫死值的問題 |
| 2026-10-23 | 2.1 修正 | `pytest -q`（Linux，Python 3.13，FFmpeg 6.1） | 115 passed, 3 skipped in 36s | Windows 實測待填 |
| 2026-10-23 | 2.1 修正 | 重現 Review #1：輸入 `clip.tmp.mp4`、輸出 `clip.mp4` | 舊版刪除輸入；新版輸入保留 | Linux |
| 2026-10-23 | 2.1 修正 | 畫面比對（fixtures） | 正確格 MAD 0.0–0.19，次佳 1.2–2.1 | 64×36 灰階 |
| 2026-10-23 | 2.1 | `pytest -q`（設定 VBALL_REAL_VIDEO，Windows） | 97 passed in 6.91s | 初版 |
| 2026-10-23 | 2.1 | 真實影片 accurate 1000–4000 | actual 1000–3967，誤差 33 ms（容許 50） | 初版，起點未量測 |
| 2026-10-23 | 2.1 | 真實影片 copy 1000–4000 | actual 998–4066，誤差 66 ms（終點） | 初版 warning 文字誤標為起點 |
| 2026-10-22 | 2.1 | `pytest -q`（Linux，Python 3.13，FFmpeg 6.1） | 94 passed, 3 skipped | 初版 |
| 2026-10-22 | 2.1 | `vball clip cfr30 1500–2500 --mode copy` | actual 1000–2500，誤差 500 ms，warning | Linux；GOP 1 秒，符合預期 |
| 2026-10-22 | 2.1 | `vball clip vfr_mixed 1200–2200` | actual 1200–2200，誤差 0 ms（容許 74 ms） | Linux |
| 2026-10-21 | 1.5 修正 | `pytest -q`（設定 VBALL_REAL_VIDEO） | 68 passed in 1.91s | Windows 實測，Review 修正驗收 |
| 2026-10-20 | 1.5 修正 | `pytest -q`（Linux，Python 3.13） | 67 passed, 1 skipped | Windows 實測待填 |
| 2026-10-20 | 1.5 | `pytest -q`（設定 VBALL_REAL_VIDEO） | 25 passed in 1.41s | Windows 實測，含真實影片 |
| 2026-10-20 | 1.5 | `pytest -q`（未設定真實影片） | 24 passed, 1 skipped | Windows 實測 |
| 2026-10-20 | 1.5 | `vball probe 20260719.mp4` | 5935 ms、872×490、avg 29.823、is_vfr_suspected false、aac | 與 ffprobe 盤點一致 |
| 2026-10-20 | 1.5 | `vball probe vfr_mixed.mp4` | avg 20.225、is_vfr_suspected true | — |
| 2026-10-20 | 1.5 | `vball probe corrupt.mp4` | `ERROR [INVALID_VIDEO]`，exit 1 | — |
| 2026-10-20 | 1.4 | `pytest -q`（volleyball） | 14 passed in 4.75s | Windows 實測；6 支 fixture 產生成功 |
| 2026-10-19 | 1.3 | `pytest -q`（volleyball，Python 3.13.13） | 6 passed in 0.09s | Windows 實測 |
| 2026-10-19 | 1.3 | `vball --version` | `vball 0.0.1` | Windows 實測 |
| 2026-10-18 | 1.1 | `python --version`（volleyball） | 3.13.13 | base 為 3.13.9，勿混用 |
| 2026-10-18 | 1.1 | `python -c "import torch, ultralytics, cv2; ..."`（volleyball 環境） | torch 2.6.0+cu124、`cuda True`；ultralytics 8.4.66；opencv 4.13.0 | — |
| 2026-10-18 | 1.1 | `ffmpeg -version` | 9.0.2-full_build，exit 0 | 含 libx264、NVENC |
| 2026-10-18 | 1.1 | `ffprobe ... 20260719.mp4` | h264 872×490、r 30/1、avg 35400/1187、5.935 s | 疑似 VFR |

## 模型指標（來源：舊訓練專案 `results.csv`，非本專案量測）

| 模型 | Precision | Recall | mAP50 | mAP50-95 | 量測資料 |
|---|---|---|---|---|---|
| exp1-4 best.pt | 0.917 | 0.687 | 0.793 | 0.463 | Volleyball_v2 驗證圖片 |

影片上的實際表現：**未量測**。
