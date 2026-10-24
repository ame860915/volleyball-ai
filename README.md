# Volleyball AI Video Analysis System

排球 AI 影片分析系統：使用者以手機固定機位錄製比賽或訓練影片，系統自動完成影片切片、Rally 切分、Highlight 與分析報告。

> **狀態：開發中（Month 1 Week 2）**
> 本專案持續快速變動，功能、結構與 API 可能隨時調整。最新進度請看 [`docs/context/PROJECT_STATUS.md`](docs/context/PROJECT_STATUS.md)（建立後生效）。

---

## 目標流程

```
Video Upload → Video Slicing → Rally Segmentation → Player / Ball Analysis
→ Event Timeline → Manual Correction → Highlight → Report → Mobile App
```

## 版本規劃

| 版本 | 目標 | 主要功能 |
|---|---|---|
| V0 | 影片切片 | FFprobe metadata、FFmpeg 切片（copy / accurate）、JSON 紀錄、CLI |
| V1（3 個月 MVP） | 完整閉環 | 上傳 → Rally 時間軸 → 人工修正 → Highlight → 報告 |
| V2（6 個月 Beta） | 球體分析 | Ball Tracking、Touch 候選、Court Homography、落點 |
| V3 | 正式產品 | 半自動計分、已驗證球速、多機位、Mobile App |

## 目前進度

- [x] 環境與既有資產盤點（Task 1.1）
- [x] Git 初始化、`.gitignore`、影片授權紀錄
- [x] `CLAUDE.md` 與 Context 文件（Task 1.2）
- [x] 專案骨架 `src/vball/`（Task 1.3）
- [x] 合成測試影片（Task 1.4）
- [x] `vball probe` 影片資訊讀取（Task 1.5）
- [ ] `vball clip` 影片切片（Task 2.1，驗收中）

## 開發環境

| 項目 | 版本 |
|---|---|
| OS | Windows（PowerShell） |
| Conda 環境 | `volleyball` |
| PyTorch | 2.6.0+cu124（CUDA 可用） |
| Ultralytics | 8.4.66 |
| OpenCV | 4.13.0 |
| FFmpeg / FFprobe | 9.0.2（gyan.dev full build，含 libx264、NVENC） |
| GPU | NVIDIA GeForce RTX 4050 Laptop（6 GB） |

詳細盤點見 [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)。

```powershell
conda activate volleyball
cd D:\2027\Volleyball\Project
```

## 使用方式

```powershell
conda activate volleyball
pip install -e ".[dev]"

# 讀取影片資訊（JSON）
vball probe <video.mp4>

# 切片：accurate 精準（預設）、copy 快速但起點對齊 Keyframe
vball clip <video.mp4> --start-ms 1000 --end-ms 4000 --out outputs/clip.mp4
vball clip <video.mp4> --start-ms 1000 --end-ms 4000 --out outputs/clip.mp4 --mode copy --overwrite

# 測試
python tests/fixtures/make_fixtures.py
pytest -q
```

每次切片會輸出 `clip.mp4`、`clip.json`（要求與實際起訖時間）、`clip.log`。

## 規劃中的專案結構

```text
Project/
├── CLAUDE.md               # Claude Code 主要入口與規則
├── README.md
├── src/vball/              # 主程式（CLI、video、adapters）
├── tests/                  # pytest 與合成測試影片
├── data/
│   └── LICENSES.md         # 影片來源與授權紀錄
└── docs/
    ├── ENVIRONMENT.md
    ├── ARCHITECTURE.md
    ├── DECISIONS.md
    ├── TEST_RESULTS.md
    └── context/            # PROJECT_STATUS、TASK_PLAN 等
```

## 資料與授權

- 影片、模型權重（`*.mp4`、`*.pt` 等）與授權證明**不進 Git**，見 `.gitignore`。
- 每支影片的來源與授權狀態記錄於 [`data/LICENSES.md`](data/LICENSES.md)。
- 只有授權狀態允許的影片可用於訓練；公開使用時須標示出處。

## 開發原則

1. Context First：先確認需求、既有程式與限制。
2. Flow First：先建立資料流，再撰寫功能。
3. Small Tasks：一次完成一個可驗收任務。
4. CLI First：核心功能先能以 CLI 執行，再整合 Web。
5. Testing First：每個模組都有測試與完成條件。
6. Human-in-the-Loop：AI 結果保留 Unknown / Uncertain 與人工修正。
7. Review：Claude Code 開發，Codex 獨立 Review。

## 授權

本 Repository 目前為私人開發專案，未開放授權。
