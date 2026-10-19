# CLAUDE.md — Volleyball AI Video Analysis System

Claude Code 的主要入口。這裡只放穩定規則與索引；細節依任務讀取 `docs/`，不要每次載入全部文件。

## 專案一句話

手機固定機位（球場後方）錄製排球影片 → 影片切片 → Rally → Highlight → 報告。Web-first，一人開發。

## 環境

- OS：Windows，指令預設 **PowerShell**（WSL / Docker 指令須明確標示）
- Conda 環境：`volleyball`（torch 2.6.0+cu124、ultralytics 8.4.66、OpenCV 4.13.0）
- FFmpeg / FFprobe 9.0.2（含 libx264、NVENC）
- Repo：`D:\2027\Volleyball\Project`，主分支 `main`，GitHub Private
- 舊訓練專案（唯讀）：`D:\2026\4.Professional\Volleyball\YoloV11_TrainVolleyball\predict`

## 硬規則

**以下動作必須先取得使用者同意：**
- 刪除或覆寫既有檔案、大型重構
- `git push`、`git push --force`、改寫已推送的歷史
- 部署、使用付費資源或雲端 GPU
- 修改 `legacy/` 或 `D:\2026\...` 舊資料夾

**永遠遵守：**
- 影片、模型權重、資料集、授權證明不進 Git（見 `.gitignore`）
- 沒有實際執行過的程式或測試，不得宣稱成功
- 速度一律標示 `pixel` 或 `projected`；未經校正驗證不得輸出 km/h
- 無法判斷的結果輸出 `unknown` / `uncertain`，不得猜測
- 未經 Ground Truth 驗證的準確率或資料量必須標示「估算」
- Superpowers 外掛未安裝，不得假裝已啟用

## 每個任務的流程（Flow First）

1. **Inspect**：讀 `PROJECT_STATUS.md`、`git status`、相關程式與測試
2. **Flow**：畫 Input → Process → Output
3. **Plan**：列出要改的檔案、函式、風險、驗收條件
4. **Implement**：最小可執行版本，CLI 優先
5. **Test**：實際執行 pytest 與 CLI
6. **Review**：產出 Review Brief（`docs/context/DEBUG_HANDOFF.md`）
7. **Update**：更新 `PROJECT_STATUS.md`、`docs/TEST_RESULTS.md`，然後 commit

**一次只做一個可驗收的 Task。** 完成定義見 `docs/context/TEST_RULES.md`。

## 文件索引

| 何時讀 | 文件 |
|---|---|
| 每次開始工作 | `docs/context/PROJECT_STATUS.md` |
| 選下一個任務 | `docs/context/TASK_PLAN.md` |
| 確認功能範圍、驗收標準 | `docs/context/REQUIREMENTS.md` |
| 模組 I/O、JSON 格式 | `docs/context/DEVELOPMENT_FLOW.md` |
| 技術選型、資料夾結構 | `docs/ARCHITECTURE.md` |
| 為什麼這樣決定 | `docs/DECISIONS.md` |
| 寫測試、判斷完成 | `docs/context/TEST_RULES.md` |
| 指令、Git 規範 | `docs/context/CLI_WORKFLOW.md` |
| 交給 Codex Review | `docs/context/AI_COLLABORATION.md`、`DEBUG_HANDOFF.md` |
| 背景與限制 | `docs/context/PROJECT_CONTEXT.md` |
| 環境盤點結果 | `docs/ENVIRONMENT.md` |
| 影片授權 | `data/LICENSES.md` |

## 常用指令

```powershell
conda activate volleyball
cd D:\2027\Volleyball\Project
pytest -q
git status
```

## 語言

技術說明用繁體中文；程式、函式、專有名詞保留英文。不易理解的 AI 概念附白話解釋。
