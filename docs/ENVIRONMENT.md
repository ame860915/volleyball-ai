# 開發環境與既有資產盤點

盤點日期：2026-10-18（Task 1.1）。本文件記錄實際執行過的檢查結果；環境變動時請更新。

## 1. 硬體

| 項目 | 結果 |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop，6 GB VRAM |
| Driver | 573.05（支援 CUDA 12.8） |

## 2. Python 環境

**開發一律使用 `volleyball` conda 環境。**

| 項目 | `volleyball` 環境 |
|---|---|
| PyTorch | 2.6.0+cu124，`torch.cuda.is_available() = True` |
| Ultralytics | 8.4.66 |
| OpenCV | 4.13.0 |
| Python | 3.13.13（`D:\Anaconda3\envs\volleyball\python.exe`） |

Anaconda `base` 環境（不使用，Python 3.13.9）匯入 torch 時出現 `OMP: Error #15`（libiomp5md.dll 重複載入），屬 base 環境套件衝突，`volleyball` 環境未出現。

**啟用確認：** 提示字元開頭必須是 `(volleyball)`。一般 PowerShell 未執行 `conda init powershell` 時，`conda activate` 不會報錯但也不會生效，會誤用 base。請使用 Anaconda PowerShell Prompt，或先執行一次 `conda init powershell`。

## 3. FFmpeg

| 項目 | 結果 |
|---|---|
| 版本 | ffmpeg 9.0.2-full_build（gyan.dev） |
| 重點編碼器 | libx264、libx265、NVENC / NVDEC、AAC |
| FFprobe | 可用 |

## 4. 新專案位置

`D:\2027\Volleyball\Project`：盤點時為空資料夾，2026-10-18 完成 `git init`。

## 5. 既有資產（唯讀，不修改）

舊訓練專案：`D:\2026\4.Professional\Volleyball\YoloV11_TrainVolleyball\predict`

| 內容 | 說明 |
|---|---|
| `train.py`、`predict.py` | 舊訓練與推論腳本 |
| `yolo11n.pt`、`yolo26n.pt` | 官方預訓練權重 |
| `VolleyballData/data.yaml` | 1 類：`volleyball`；train / valid / test 三組 |
| `runs/detect/volleyball_runs/exp1-4/weights/best.pt` | 自訓球偵測模型 |

### 球偵測模型 exp1-4

| 參數 / 指標 | 值 |
|---|---|
| 基底模型 | yolo11n.pt |
| epochs / batch / imgsz | 100 / 8 / 640 |
| 訓練時間 | 132,870 秒（約 37 小時） |
| Precision | 0.917 |
| Recall | 0.687 |
| mAP50 | 0.793 |
| mAP50-95 | 0.463 |

- 指標來自驗證圖片，**未在實際比賽影片上量測**。
- Recall 偏低（約 3 成漏抓），Month 4 以 Kalman 插補、提高 imgsz、Tiling 改善。
- 已知不一致：`args.yaml` 與舊 `predict_ball.py` 的路徑寫的是 `YoloV11_TrainMySelf` 與 `Data/data.yaml`，與目前實際位置不同。新系統一律以設定檔指定模型路徑。

## 6. 測試影片

| 項目 | 20260719.mp4 |
|---|---|
| 位置 | `...\YoloV11_TrainVolleyball\VolleyballData\Video\20260719.mp4`（不進 Git） |
| 編碼 | H.264 / AAC |
| 解析度 | 872 × 490 |
| 長度 | 5.935 秒，1.63 MB |
| FPS | r_frame_rate 30/1；avg_frame_rate 35400/1187 ≈ 29.82 |
| 授權 | 見 `data/LICENSES.md` |

r_frame_rate 與 avg_frame_rate 不一致，代表有輕微 VFR 或掉幀；切片必須以時間戳計算，不能以「影格數 ÷ 30」換算。

## 7. 待補

- 至少一支 10 分鐘以上、固定機位（球場後方）的完整比賽影片，供 Rally 與 Highlight 開發使用。
