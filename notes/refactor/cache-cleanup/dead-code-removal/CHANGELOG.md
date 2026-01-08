# Changelog: Dead Code Removal

## [Unreleased] - 2026-01-08

### Removed
- `app/services/cached_financial.py` (120 行)
  - 死程式碼，從未被任何地方使用
  - `CachedFinancialService` 與 `FinancialService` 邏輯重複
  - 刪除後減少維護負擔

### Verified
- `FinancialService.get_financial_statement()` 已包含完整的 cache-first 邏輯：
  1. 先查詢資料庫
  2. 快取未命中時從 MOPS 下載
  3. 下載後儲存到資料庫

### Tests
- 45 tests passed
- 無 import 錯誤
