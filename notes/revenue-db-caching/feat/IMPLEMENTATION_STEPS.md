# Revenue DB Caching - Implementation Steps

## Step 1: 修正 Import 路徑

### 任務
- 修正 `app/db/repository.py` 中 `MonthlyRevenueSchema` 的 import 路徑
- 舊路徑: `from app.services.revenue import MonthlyRevenue`
- 新路徑: `from app.schemas.revenue import MonthlyRevenue`

### 驗證
```bash
uv run python -c "from app.db.repository import RevenueRepository; print('OK')"
```

---

## Step 2: 改造 RevenueService

### 任務
- 在 `app/services/revenue.py` 中:
  1. Import `get_session` 和 `RevenueRepository`
  2. 修改 `get_market_revenue()` 加入 DB 快取邏輯
  3. 新增 `force_refresh` 參數
  4. 將原本的爬取邏輯抽成 `_fetch_from_mops()` 私有方法

### 驗證
```bash
uv run python -c "from app.services.revenue import RevenueService; print('OK')"
```

---

## Step 3: 更新 Router

### 任務
- 在 `app/routers/revenue.py` 中:
  1. 新增 `force_refresh` Query 參數
  2. 傳遞到 Service

### 驗證
```bash
uv run python -c "from app.routers.revenue import router; print('OK')"
```

---

## Step 4: 更新 DB __init__ exports

### 任務
- 在 `app/db/__init__.py` 中新增 `RevenueRepository` 的 export

### 驗證
```bash
uv run python -c "from app.db import RevenueRepository; print('OK')"
```

---

## Step 5: 執行測試

### 驗證
```bash
uv run pytest tests/test_revenue_service.py -v
```

---

## 檢查點

| Step | 狀態 | 備註 |
|------|------|------|
| Step 1: 修正 Import | ⬜ | |
| Step 2: 改造 Service | ⬜ | |
| Step 3: 更新 Router | ⬜ | |
| Step 4: 更新 exports | ⬜ | |
| Step 5: 測試通過 | ⬜ | |
