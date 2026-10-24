# TEST_RESULTS

只記錄**實際執行過**的結果。新紀錄加在最上方。

| 日期 | Task | 指令 | 結果 | 備註 |
|---|---|---|---|---|
| 2026-10-22 | 2.1 | `pytest -q`（Linux，Python 3.13，FFmpeg 6.1） | 94 passed, 3 skipped | Windows 實測待填 |
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
