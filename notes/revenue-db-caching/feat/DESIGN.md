# Revenue DB Caching - Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ GET /revenue/monthly?year=113&month=12&stock_id=2330    ││
│  └───────────────────────────┬─────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               RevenueService (改造)                      ││
│  │  ┌───────────────────────────────────────────────────┐  ││
│  │  │ get_market_revenue(year, month, market,           │  ││
│  │  │                    force_refresh=False)           │  ││
│  │  │                                                   │  ││
│  │  │   1. Check DB via RevenueRepository               │  ││
│  │  │   2. If found & !force_refresh → return cached   │  ││
│  │  │   3. If not found → fetch MOPS → save to DB      │  ││
│  │  └───────────────────────────────────────────────────┘  ││
│  └───────────────────────────┬─────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               RevenueRepository (已存在)                 ││
│  │  - save_revenues()                                      ││
│  │  - get_revenue()                                        ││
│  │  - get_market_revenues()                                ││
│  │  - revenue_exists()                                     ││
│  └───────────────────────────┬─────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           PostgreSQL (mops_financial_db)                ││
│  │  Table: monthly_revenue                                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. RevenueService 改造

**新增參數:**
- `force_refresh: bool = False` - 強制從 MOPS 重新爬取

**改造邏輯:**
```python
async def get_market_revenue(
    self,
    year: int,
    month: int,
    market: str = "sii",
    company_type: int = 0,
    force_refresh: bool = False,
) -> List[MonthlyRevenue]:
    
    # 1. 先檢查 DB (除非 force_refresh)
    if not force_refresh:
        async with get_session() as session:
            repo = RevenueRepository(session)
            cached = await repo.get_market_revenues(year, month, market)
            if cached:
                logger.info(f"Cache hit: {year}/{month} from DB ({len(cached)} records)")
                return cached
    
    # 2. DB 沒有，從 MOPS 爬取
    revenues = await self._fetch_from_mops(year, month, market, company_type)
    
    # 3. 存入 DB
    async with get_session() as session:
        repo = RevenueRepository(session)
        await repo.save_revenues(revenues, market)
    
    return revenues
```

### 2. API Router 改造

**新增 Query 參數:**
```python
@router.get("/monthly")
async def get_monthly_revenue(
    ...,
    force_refresh: bool = Query(False, description="強制重新從 MOPS 爬取"),
):
```

## Data Flow

1. **Cache Hit**: API → Service → Repository → DB → Return
2. **Cache Miss**: API → Service → Repository (miss) → MOPS → Repository (save) → Return

## Error Handling

- DB 連線失敗時，fallback 到直接爬 MOPS（不存快取）
- MOPS 爬取失敗時，若 DB 有舊資料可考慮回傳（optional）
