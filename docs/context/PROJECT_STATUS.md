# PROJECT_STATUS

最後更新：2026-10-19

## 目前位置

**Phase 0 / Month 1 Week 1 — Task 1.5（`vball probe`）待驗收**

## 已完成

| Task | 內容 | 完成日 | 驗收證據 |
|---|---|---|---|
| 1.1 | 環境與既有資產盤點 | 2026-10-18 | `docs/ENVIRONMENT.md` |
| — | Git 初始化、`.gitignore`、`data/LICENSES.md`，清除 4 GB 誤加入的資料集物件 | 2026-10-19 | commit `345cb9f` |
| — | README、環境文件，推送至 GitHub Private repo | 2026-10-19 | `origin/main` |
| 1.2 | `CLAUDE.md` 與 13 份 Context 文件 | 2026-10-19 | 已推送 |
| 1.3 | 專案骨架 `pyproject.toml`、`src/vball/`、`tests/` | 2026-10-19 | `pytest -q` 6 passed；`vball 0.0.1`；commit `5c3633b` |
| 1.4 | 6 支合成測試影片與規格驗證 | 2026-10-20 | `pytest -q` 14 passed（Windows） |

## 進行中

- [ ] 1.5 `vball probe` — 待在 Windows 執行驗收（含真實影片 `20260719.mp4`）

## 下一步

- [ ] Week 1 收尾：Codex Review Task 1.5
- [ ] Week 2：`vball clip`（copy / accurate）+ 9 類測試案例

## 已知問題與待確認

| # | 項目 | 影響 | 處理時機 |
|---|---|---|---|
| 1 | 一般 PowerShell 的 `conda activate` 可能未生效而誤用 base | 套件與 CUDA 錯誤 | 已寫入 CLI_WORKFLOW，每次確認 `(volleyball)` |
| 2 | 舊 `args.yaml`、`predict_ball.py` 路徑與實際資料夾不一致 | 新系統以設定檔指定路徑即可 | W9 |
| 3 | 球模型 Recall 0.687，且未在實際影片量測 | 球軌跡會漏抓 | Month 4 |
| 4 | 測試影片僅 5.9 秒、872×490、輕微 VFR | 不足以開發 Rally | Month 2 前取得完整比賽影片 |
| 5 | `20260719.mp4` 拍攝者同意與商用授權待確認 | 不可用於商用或對外 Demo | 對外展示前 |
| 6 | Volleyball_v2 資料集由多個來源合併，個別授權未逐一確認 | 商用前需確認 | Beta 前 |
