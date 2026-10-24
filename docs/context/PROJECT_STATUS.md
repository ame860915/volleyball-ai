# PROJECT_STATUS

最後更新：2026-10-22

## 目前位置

**Month 1 Week 2 — Task 2.1（`vball clip`）待 Windows 驗收**

## 已完成

| Task | 內容 | 完成日 | 驗收證據 |
|---|---|---|---|
| 1.1 | 環境與既有資產盤點 | 2026-10-18 | `docs/ENVIRONMENT.md` |
| — | Git 初始化、`.gitignore`、`data/LICENSES.md`，清除 4 GB 誤加入的資料集物件 | 2026-10-19 | commit `345cb9f` |
| — | README、環境文件，推送至 GitHub Private repo | 2026-10-19 | `origin/main` |
| 1.2 | `CLAUDE.md` 與 13 份 Context 文件 | 2026-10-19 | 已推送 |
| 1.3 | 專案骨架 `pyproject.toml`、`src/vball/`、`tests/` | 2026-10-19 | `pytest -q` 6 passed；`vball 0.0.1`；commit `5c3633b` |
| 1.4 | 6 支合成測試影片與規格驗證 | 2026-10-20 | `pytest -q` 14 passed（Windows） |
| 1.5 | `vball probe`：VideoMetadata、錯誤代碼、VFR 判斷；依 Codex Review 修正 6 項 | 2026-10-21 | `pytest -q` 68 passed（Windows，含真實影片） |

## 進行中

- [ ] 2.1 `vball clip`（copy / accurate、.tmp 原子寫入、JSON + log）— 待 Windows 驗收與 Review

## 下一步

- [ ] Week 3：批次切片（CSV / JSON 清單）、逐格時間戳 VFR 分析、log 彙整

## 已知問題與待確認

| # | 項目 | 影響 | 處理時機 |
|---|---|---|---|
| 1 | 一般 PowerShell 的 `conda activate` 可能未生效而誤用 base | 套件與 CUDA 錯誤 | 已寫入 CLI_WORKFLOW，每次確認 `(volleyball)` |
| 2 | 舊 `args.yaml`、`predict_ball.py` 路徑與實際資料夾不一致 | 新系統以設定檔指定路徑即可 | W9 |
| 3 | 球模型 Recall 0.687，且未在實際影片量測 | 球軌跡會漏抓 | Month 4 |
| 4 | 測試影片僅 5.9 秒、872×490；r 與 avg 差 0.6%（低於 1% 門檻，判定非 VFR，可能為少量掉幀） | 不足以開發 Rally | Month 2 前取得完整比賽影片 |
| 7 | VFR 判斷門檻 1% 未經多支手機影片驗證 | 可能誤判 | 取得更多真實影片後調整 |
| 5 | `20260719.mp4` 拍攝者同意與商用授權待確認 | 不可用於商用或對外 Demo | 對外展示前 |
| 6 | Volleyball_v2 資料集由多個來源合併，個別授權未逐一確認 | 商用前需確認 | Beta 前 |
