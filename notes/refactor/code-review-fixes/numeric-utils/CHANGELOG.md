# Changelog: numeric-utils Refactoring

## [Unreleased] - 2026-01-08

### Added
- `app/utils/numerics.py` - 統一的數值解析工具模組
  - `parse_financial_value()` - 解析財報數值字串為 Decimal
  - `is_numeric_string()` - 快速檢查字串是否為有效數值
- `tests/test_numerics.py` - 26 個單元測試覆蓋所有邊界條件

### Changed
- `app/services/xbrl_parser.py` - 使用統一的字串清理邏輯
- `app/services/financial.py` - 替換 4 處重複的數值解析邏輯
- `app/routers/financial.py` - 替換 simplified API 中的數值解析

### Fixed
- 消除數值解析的 DRY 違規 (CODE_REVIEW Critical Issue)
- 統一處理半形 `-` 和全形 `—` 破折號

### Technical Notes
- 所有數值現統一使用 `Decimal` 型別以保持精度
- 無 API 行為變更，完全後向相容
