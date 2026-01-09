# Revenue DB Caching - 需求定義

## Feature Description

讓 `RevenueService` 支援資料庫快取功能，實現「先查 DB，沒有才爬 MOPS」的邏輯。

## User Stories

1. **作為開發者**，我希望月營收資料能被快取到 PostgreSQL，這樣可以減少對 MOPS 的請求並加快回應速度。
2. **作為 API 使用者**，我希望查詢月營收時，系統能自動判斷是否需要從 MOPS 爬取資料。

## Use Cases

### UC1: Query with Auto-Caching

```
User → API (/revenue/monthly?year=113&month=12)
       ↓
RevenueService.get_market_revenue()
       ↓
   [Check DB via RevenueRepository]
       ↓
   Found? → Return cached data
   Not Found? → Fetch from MOPS → Save to DB → Return
```

## Acceptance Criteria

- [ ] `RevenueService` 使用 `RevenueRepository` 進行資料庫操作
- [ ] 查詢時先檢查 DB，沒有則爬取並存入
- [ ] 提供 `force_refresh` 參數強制重新爬取
- [ ] 保持現有 API 介面不變
- [ ] 增加必要的測試

## Dependencies

- `app/db/repository.py` - `RevenueRepository` (已存在)
- `app/db/models.py` - `MonthlyRevenue` DB Model (已存在)
- `app/db/connection.py` - Database session management (已存在)
