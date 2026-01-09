# Changelog: Remove Q4 Standalone Calculation

## [Unreleased]

### Removed
- **Q4 單季計算功能**: 移除了「年報 - Q3 累積」的預先計算邏輯
  - 刪除 `FinancialService.CUMULATIVE_REPORTS` 常數
  - 刪除 `FinancialService._get_q4_standalone()` 方法（約 50 行）
  - 簡化 `get_financial_statement()` 流程

### Changed
- **API 行為**: 所有端點現在直接返回 MOPS 解析後的原始報表數據
  - `GET /{stock_id}/income-statement?quarter=4` 現在返回 Q4 原始累計數據
  - `GET /{stock_id}/equity-statement?quarter=4` 同上
- **文檔更新**: 更新所有端點的 docstring 以反映新行為

### Benefits
- 減少每次 Q4 請求的額外 API 呼叫（不再需要下載 Q3）
- 降低維護複雜度
- 用戶可以根據需求自行計算單季數據
