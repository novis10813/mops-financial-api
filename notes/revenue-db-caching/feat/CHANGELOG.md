# Revenue DB Caching - 變更日誌

## 2026-01-09

### ✅ 新增功能

#### DB 快取整合

- **RevenueService** 現在會自動快取月營收資料到 PostgreSQL
- 查詢邏輯: 先查 DB，沒有才爬 MOPS，爬完存入 DB
- 新增 `force_refresh` 參數可強制重新爬取

#### API 變更

- `GET /revenue/monthly` 新增 `force_refresh` Query 參數
- `GET /revenue/monthly/{stock_id}` 新增 `force_refresh` Query 參數

### 📁 變更檔案

| 檔案 | 變更 |
|------|------|
| `app/services/revenue.py` | 整合 RevenueRepository，新增 `_fetch_from_mops()` |
| `app/routers/revenue.py` | 新增 `force_refresh` 參數 |
| `app/db/repository.py` | 修正 import 路徑 |
| `app/db/__init__.py` | 新增 RevenueRepository export |

### 📊 測試

- 10 tests passed ✅
