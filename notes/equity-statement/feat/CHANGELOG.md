# Changelog

## [Unreleased]

### Added
- 新增權益變動表 (Statement of Changes in Equity) 端點
  - `GET /financial/{stock_id}/equity-statement` - 取得權益變動表
  - 支援 `year` 和 `quarter` 參數
  - 支援 `tree` / `flat` 輸出格式
  - 支援 Q4 單季計算（累計型報表）
  - 支援資料庫快取
- FinMind 格式支援 `equity_statement` 類型
