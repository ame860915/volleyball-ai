# PROJECT_STATUS

最後更新：2026-10-19

## 目前位置

**Phase 0 / Month 1 Week 1 — Task 1.2（Context 文件）**

## 已完成

| Task | 內容 | 完成日 | 驗收證據 |
|---|---|---|---|
| 1.1 | 環境與既有資產盤點 | 2026-10-18 | `docs/ENVIRONMENT.md` |
| — | Git 初始化、`.gitignore`、`data/LICENSES.md`，清除 4 GB 誤加入的資料集物件 | 2026-10-19 | commit `345cb9f` |
| — | README、環境文件，推送至 GitHub Private repo | 2026-10-19 | `origin/main` |

## 進行中

- [ ] 1.2 `CLAUDE.md` 與 Context 文件 — 待使用者審閱後 commit

## 下一步

- [ ] 1.3 專案骨架：`src/vball/`、`tests/`、`pyproject.toml`，`pytest` 可執行
- [ ] 1.4 合成測試影片（30fps、60fps、VFR、無音訊、0 秒、損壞檔）
- [ ] 1.5 `vball probe`

## 已知問題與待確認

| # | 項目 | 影響 | 處理時機 |
|---|---|---|---|
| 1 | `volleyball` 環境 Python 版本未記錄 | `pyproject.toml` 的 `requires-python` | Task 1.3 |
| 2 | 舊 `args.yaml`、`predict_ball.py` 路徑與實際資料夾不一致 | 新系統以設定檔指定路徑即可 | W9 |
| 3 | 球模型 Recall 0.687，且未在實際影片量測 | 球軌跡會漏抓 | Month 4 |
| 4 | 測試影片僅 5.9 秒、872×490、輕微 VFR | 不足以開發 Rally | Month 2 前取得完整比賽影片 |
| 5 | `20260719.mp4` 拍攝者同意與商用授權待確認 | 不可用於商用或對外 Demo | 對外展示前 |
| 6 | Volleyball_v2 資料集由多個來源合併，個別授權未逐一確認 | 商用前需確認 | Beta 前 |
