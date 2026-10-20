# CLI_WORKFLOW

## 指令環境標示

所有指令預設 **Windows PowerShell**。其他環境必須在程式碼區塊第一行註明：

```powershell
# Windows PowerShell（預設）
```

```bash
# WSL Ubuntu
```

```bash
# Docker
```

## 每次開始工作

```powershell
conda activate volleyball
cd D:\2027\Volleyball\Project
git status
git pull
```

## Python

- 一律使用 `volleyball` conda 環境，不使用 Anaconda `base`（有 OMP 衝突）。
- **執行任何指令前，先確認提示字元開頭是 `(volleyball)`。** 不確定時執行 `where.exe python`，第一行必須是 `...\envs\volleyball\python.exe`。
- 專案以 `pip install -e ".[dev]"` 安裝，修改程式後不需重裝。
- 套件新增後記錄到 `pyproject.toml`，不手動散裝安裝。
- 不設定 `KMP_DUPLICATE_LIB_OK=TRUE` 這類掩蓋錯誤的環境變數。

## FFmpeg

- 由 Python `subprocess` 呼叫，參數用 list 傳入，不組字串（避免路徑空白與中文問題）。
- 一律加 `-hide_banner -nostdin`；切片時加 `-y` 只寫入 `.tmp` 暫存檔。
- 時間參數用秒（小數點後 3 位），由毫秒換算。

## Git

| 規則 | 說明 |
|---|---|
| 分支 | `main` 為穩定版；功能開發用 `feat/<task-id>-<name>`，例如 `feat/1.5-probe` |
| Commit 訊息 | `feat:`、`fix:`、`docs:`、`test:`、`chore:`、`refactor:` 開頭 |
| Commit 頻率 | 每完成一個可驗收的小步驟 |
| Push | 驗收通過後；需使用者同意 |
| 禁止 | 未經同意 `push --force`、改寫已推送歷史、提交影片 / 模型 / 資料集 |

提交前檢查：

```powershell
git status
git diff --stat --cached
pytest -q
```

## 大檔案

新增任何超過 10 MB 的檔案前，先確認已被 `.gitignore` 排除：

```powershell
git check-ignore -v <檔案路徑>
```
