# Changelog: service-layer-refactor

## [Unreleased] - 2026-01-08

### Added
- `FinancialService.get_simplified_statement()` - 取得 FinMind 風格財報
- `FinancialService._convert_to_simplified()` - XBRLPackage 轉換邏輯

### Changed
- `app/routers/financial.py` - 簡化 `get_simplified_statement()` endpoint
  - 移除內部 import 和業務邏輯（減少 ~60 行）
  - 委派給 `FinancialService`
  - 與其他 endpoint 風格一致

### Fixed
- 消除業務邏輯洩漏至 Router 的架構問題 (CODE_REVIEW High Issue)

### Technical Notes
- 無 API 行為變更，完全後向相容
- Router 現僅負責 HTTP 請求處理和驗證
