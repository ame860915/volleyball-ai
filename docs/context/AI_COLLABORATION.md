# AI_COLLABORATION

## 分工

| 角色 | 負責 | 不做 |
|---|---|---|
| **Claude Code**（本機，D14） | 架構、實作、整合、在 Windows 實際執行 pytest / CLI、修 bug、更新文件、本機 commit | 自行宣稱 Review 通過；未經同意 push |
| **claude.ai 對話** | 規劃、需求與設計討論 | 修改程式或交付 zip（D14 起停止） |
| **Codex** | Code Review、Bug 調查、效能、Edge case、測試覆蓋、可維護性 | 直接修改 Claude Code 正在開發的分支 |
| **使用者** | 決定範圍、審閱、驗收、同意 push / 刪除 / 付費資源 | — |

## 分支規則

- Claude Code 在 `feat/<task-id>-*` 開發。
- Codex 的修改建議放在 `review/<task-id>`，或只以文字回報；由使用者決定是否合併。
- 兩者不得同時修改同一分支或同一檔案。

## 交接流程

1. Claude Code 完成 Task 並通過 `TEST_RULES.md` 的 DoD。
2. Claude Code 在 `DEBUG_HANDOFF.md` 新增一筆 Review Brief。
3. 使用者把 Review Brief 貼給 Codex（範本見下方）。
4. Codex 回報問題清單，使用者轉回 Claude Code 修正。
5. 修正結果補記在同一筆 Review Brief 下。

## 給 Codex 的提示詞範本

```text
你是這個 Repository 的獨立 Code Reviewer，不要直接修改 main 或 feat/* 分支。
請先讀 CLAUDE.md 與 docs/context/DEBUG_HANDOFF.md 最新一筆 Review Brief。

請檢查：
1. 功能是否符合 Requirement 與驗收條件
2. Bug 與 Edge case（特別是錯誤處理、路徑、VFR、中文路徑）
3. 測試是否足夠，缺哪些案例
4. 效能與可維護性問題

回報格式：
- Severity（High / Medium / Low）
- 檔案與行號
- 問題說明
- 建議修正（文字或 diff，不直接提交）
```
