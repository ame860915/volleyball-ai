# TASK_PLAN

24 週任務的唯一來源。以每週 10–12 小時估算，屬規劃假設。進度記錄在 `PROJECT_STATUS.md`，這裡只放計畫。

## Month 1 Week 1（細分）

| Task | 內容 | 驗收 |
|---|---|---|
| 1.1 | 環境與既有資產盤點 | `docs/ENVIRONMENT.md` |
| 1.2 | `CLAUDE.md` 與 Context 文件 | 使用者審閱同意後 commit |
| 1.3 | 專案骨架 `src/vball/`、`tests/`、`pyproject.toml` | `pytest` 可執行 |
| 1.4 | `tests/fixtures/make_fixtures.py` 合成 6 支測試影片 | 30fps、60fps、VFR、無音訊、0 秒、損壞檔產生成功 |
| 1.5 | `vball probe` | 6 支 fixture 輸出正確或明確錯誤 |

## 24 週總表

| 週 | 任務 | 驗收重點 | 落後時可刪 |
|---|---|---|---|
| W1 | 盤點、骨架、Context、`probe` | `vball probe` 正確 | — |
| W2 | `clip`（copy/accurate）+ 驗證 + JSON | 9 類測試案例通過 | — |
| W3 | 批次切片、VFR 處理、log | 10 段批次輸出正確 | 批次 |
| W4 | FastAPI 上傳 + 切片 API + 網頁預覽 | 瀏覽器可上傳、切片、播放 | 美化 |
| W5 | SQLite 資料模型 Video/Rally/Clip | CRUD 測試通過 | — |
| W6 | 時間軸 UI：手動標記 Rally | 一場比賽可完整標記 | 快捷鍵 |
| W7 | 規則式 Rally 候選 | 與人工標記比對 IoU | 改純手動 |
| W8 | Highlight v1：規則評分 + concat | 精華 MP4 可播放 | 轉場 |
| W9 | YOLO11 Adapter + Detection JSON | 舊模型經 Adapter 輸出正確 | — |
| W10 | Player Tracking（ByteTrack） | ID switch 有紀錄 | Re-ID |
| W11 | Pose 候選 + 簡易統計 | 每個 Rally 附人物資料 | 動作分類 |
| W12 | 報告 v1 + MVP Demo | 上傳→報告跑通 | Pose |
| W13 | 球體標註補強（估算 1–2k frame） | 標註規範與切分完成 | — |
| W14 | Ball Detection 再訓練 / 評估 | 在影片 Golden Set 記錄 P/R | — |
| W15 | Ball Tracking（Kalman + 插補） | 軌跡遺失率有紀錄 | TrackNet |
| W16 | Touch 候選 | 與人工 Touch 比對 | — |
| W17 | Court Keypoints（手動 4 點） | 重投影誤差有紀錄 | 自動偵測 |
| W18 | Court 座標 + Landing 候選 | In/Out/Uncertain | Heatmap |
| W19 | 速度 pixel→projected 可行性 | 誤差分析，不宣稱 km/h | 真實速度 |
| W20 | Highlight v2（Touch/動作） | 使用者接受率 | — |
| W21 | 計分候選 + 修正 UI | 可修正 | 失誤原因 |
| W22 | 效能（GPU、批次、快取） | 處理時間有紀錄 | — |
| W23 | Golden Set 回歸 + Bug 修正 | 指標報告 | — |
| W24 | Beta 打包、文件、試用 | 3–5 位試用者完成流程 | — |

**加速方案（每週 20 小時）：** W9–W11 提前到 Month 2 與 Rally 平行，Month 6 多出兩週嘗試 Action Recognition。

## Gate

| Gate | 時間 | 通過條件 | 未通過 |
|---|---|---|---|
| MVP | W12 | 一支完整比賽影片從上傳到報告跑通 | 不進入球體追蹤，先補閉環 |
| Beta | W24 | 3–5 位試用者完成流程並回饋 | 延後 App，縮小範圍 |
