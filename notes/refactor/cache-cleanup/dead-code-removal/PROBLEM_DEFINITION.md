# Problem Definition: Dead Code Removal

## Background

在 CODE_REVIEW 中發現資料庫應用邏輯分散的問題。經過分析：

## 現狀分析

### `app/services/financial.py` (500 行)
- `FinancialService.get_financial_statement()` **已包含完整的快取邏輯**：
  1. 先查詢資料庫（L84-102）
  2. 快取未命中時從 MOPS 下載（L104-116）
  3. 下載後儲存到資料庫（L127-134）
- Router 端點使用 `get_financial_service()` ✅

### `app/services/cached_financial.py` (120 行)
- `CachedFinancialService` 繼承 `FinancialService`
- 實現**完全相同的快取邏輯**（重複）
- **從未被使用**（Router 沒有 import）

## Pain Points

1. **死程式碼**: `cached_financial.py` 從未被使用
2. **邏輯重複**: 兩個檔案有相同的 cache-first 邏輯
3. **維護負擔**: 修改快取邏輯需要同步兩處（但沒人知道要同步）
4. **混淆開發者**: 不清楚應該用哪個 Service

## Goals

1. 刪除 `cached_financial.py` 死程式碼
2. 確認 `FinancialService` 的快取邏輯正確
3. 清理相關的 import/export

## Constraints

- 不改變 Router 的行為
- 不影響現有測試
- 保持 `FinancialService` API 不變
