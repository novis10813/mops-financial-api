# Remove Q4 Standalone Calculation Feature

## Feature Description

移除 API 端點中「年報 - Q3 累積」的預先計算功能，讓端點只返回從 MOPS 解析後的原始報表數據，不進行任何計算轉換。

## Background

在研究財報後，發現 Q4 單季計算（年報 - Q3 累積）的邏輯存在不合理之處：
- 不同報表的會計項目可能有不同的累計邏輯
- 預先計算可能導致數據不一致
- 用戶可能更需要原始數據來進行自己的分析

## User Stories

### US-1: 作為 API 使用者
- 我希望端點返回 MOPS 原始解析的財報數據
- 這樣我可以根據自己的需求進行計算和分析

### US-2: 作為維護者
- 我希望簡化 Service 層的邏輯
- 減少額外的 API 呼叫（目前 Q4 需要額外下載 Q3）
- 降低維護複雜度

## Acceptance Criteria

### AC-1: 移除 Q4 計算邏輯
- [ ] 刪除 `CUMULATIVE_REPORTS` 常數
- [ ] 刪除 `_get_q4_standalone()` 方法
- [ ] 修改 `get_financial_statement()` 移除 Q4 特殊處理分支

### AC-2: 更新端點文檔
- [ ] 更新 `financial.py` 中所有端點的 docstring
- [ ] 移除關於「Q4 自動計算單季」的說明
- [ ] 移除 `is_standalone` 相關的描述

### AC-3: 清理 Schema（如適用）
- [ ] 評估 `is_standalone` 字段是否需要保留（可能作為 future flag）

### AC-4: 更新測試
- [ ] 確保現有測試通過
- [ ] 移除或更新與 Q4 計算相關的測試

## Dependencies

- 無外部依賴
- 影響範圍：
  - `app/routers/financial.py`
  - `app/services/financial.py`
  - 相關測試文件

## Out of Scope

- 不改變 XBRL 解析邏輯
- 不改變資料庫快取機制
- 不改變 API 回應結構（除了移除不必要的標記）
