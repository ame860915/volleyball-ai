# TEST_RULES

## 完成定義（Definition of Done）

一個 Task 必須全部符合才算完成：

1. 程式在 `volleyball` 環境**實際執行過**，並附上輸出。
2. `pytest -q` 全部通過，新功能有對應測試。
3. CLI 指令可重現，預期輸出寫在 `docs/TEST_RESULTS.md`。
4. 異常情況有明確錯誤代碼，不靜默失敗。
5. `PROJECT_STATUS.md` 已更新。
6. 已 commit；需要時產出 Review Brief。

## 測試資料分層

| 層 | 內容 | 位置 | 進 Git |
|---|---|---|---|
| Synthetic fixtures | FFmpeg 合成的短影片（產生腳本） | `tests/fixtures/make_fixtures.py` | 腳本進，影片不進 |
| Real samples | 授權影片（如 `20260719.mp4`） | 本機路徑，由設定檔指定 | 否 |
| Golden Set | 人工標註、作為準確率依據的固定影片與標註 | `data/golden/`（之後建立） | 只有標註 JSON |

沒有 Real sample 時，測試標記為 `@pytest.mark.real_video` 並自動跳過，不得視為失敗或成功。

## V0 切片必測案例

| # | 案例 | 預期 |
|---|---|---|
| 1 | 正常時間區間 | 輸出可播放，boundary error 在容許值內 |
| 2 | start ≥ end | `INVALID_RANGE` |
| 3 | end 超過影片長度 | `INVALID_RANGE` |
| 4 | 不存在的檔案 | `INPUT_NOT_FOUND` |
| 5 | 空 / 損壞影片 | `INVALID_VIDEO` |
| 6 | 30fps 與 60fps | 皆正確 |
| 7 | VFR 影片 | 以時間戳計算，JSON 標記 `is_vfr_suspected` |
| 8 | 輸出路徑不可寫 | `OUTPUT_NOT_WRITABLE` |
| 9 | 重複執行 | 預設 `OUTPUT_EXISTS`；`--overwrite` 才覆蓋 |

容許值（初始，待實測調整）：accurate 模式 ≤ 1.5 frame（依 fps_avg 計算，VFR 影片僅供參考）；copy 模式只記錄誤差，不設上限，且一律 `frame_accurate = false`。

**實際邊界必須有證據**：起點以畫面比對量測（`start_basis = measured`）才可宣稱 `frame_accurate`；畫面不動或相鄰格太像時為 `estimated`，不得宣稱精準。

## 指標原則

沒有 Ground Truth 時，不得填寫準確率；只記錄「未量測」。
