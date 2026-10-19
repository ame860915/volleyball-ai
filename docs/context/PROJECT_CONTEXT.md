# PROJECT_CONTEXT

## 產品

**Volleyball AI Video Analysis System**：使用者以手機固定機位錄製排球比賽或訓練影片，上傳後由系統完成切片、Rally 切分、Highlight 與分析報告。

- 目標使用者（初期假設，待驗證）：業餘球隊、教練、個人球員
- 第一版機位：固定手機、球場後方視角
- 平台：Web-first；App 於確認產品價值後（V3）開發

## 開發者背景

AOI / Machine Vision / 傳統影像處理演算法工程師。

| 熟悉（不需從頭教） | 需要詳細指引 |
|---|---|
| C#、.NET、HALCON、OpenCV | PyTorch、模型訓練、Video AI |
| ROI、Blob、Threshold、Edge、Morphology | Tracking、Pose、Action Recognition |
| 特徵量測、座標轉換、相機與影像品質 | FastAPI、Web App、資料庫 |
| 演算法 Pipeline、多執行緒、軟硬體整合 | Docker、GPU 部署、SaaS |

說明 AI 概念時，優先用影像處理的類比（例如 Adapter ≈ HALCON 外包一層 Interface）。

## 限制

| 項目 | 限制 |
|---|---|
| 人力 | 一人開發，每週約 10–12 小時（加速方案 20 小時） |
| 時程 | 3 個月 MVP Demo、6 個月 Beta（規劃假設，非保證） |
| 運算 | 本機 RTX 4050 Laptop 6 GB；雲端 GPU 需另行同意 |
| 資料 | 小型資料集優先；每支影片須記錄授權（`data/LICENSES.md`） |
| 範圍 | 工作量過大時主動縮小功能，不阻擋切片與 Highlight 的交付 |

## 既有資產

舊球偵測模型與資料集詳見 `docs/ENVIRONMENT.md`；授權見 `data/LICENSES.md`。
