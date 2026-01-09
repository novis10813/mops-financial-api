# Additional MOPS Crawlers - Implementation Steps

本文件按照優先順序安排實作步驟，採用增量式開發方式。

---

## 檢查點 (Progress Tracker)

| Step | 任務 | 狀態 |
|------|------|------|
| 0 | 基礎設施: MOPS HTML Client | ✅ |
| 1 | P0: 月營收 - Service | ✅ |
| 2 | P0: 月營收 - Router | ✅ |
| 3 | P0: 月營收 - Database | ✅ |
| 4 | P0: 月營收 - Tests | ✅ |
| 5 | P1: 董監事質押 - Service | ✅ |
| 6 | P1: 董監事質押 - Router | ✅ |
| 7 | P1: 董監事質押 - Database | ✅ |
| 8 | P1: 董監事質押 - Tests | ✅ |
| 9 | P1: 背書保證 - Service | ✅ |
| 10 | P1: 背書保證 - Router | ✅ |
| 11 | P1: 背書保證 - Database | ✅ (共用 Disclosure) |
| 12 | P1: 背書保證 - Tests | ✅ |
| 13 | P2: 股利分派 - Full Stack | ✅ |
| 14 | P2: 資金貸與 - Full Stack | ✅ (與背書保證合併) |
| 15 | P3: 衍生性商品 - Full Stack | 🔜 |
| 16 | P3: 資本形成 - Full Stack | 🔜 |
| 17 | 整合測試與文檔 | ⬜ |

---

## Step 0: 基礎設施 - MOPS HTML Client

建立通用的 HTML 表格爬取客戶端。

### 任務

1. **建立 `app/services/mops_html_client.py`**
   - `MOPSHTMLClient` 類別
   - `fetch_html_table()` 方法 - 抓取並解析 HTML 表格
   - `fetch_static_html()` 方法 - 抓取靜態 HTML 頁面 (月營收用)
   - Rate limiting 機制 (1 req/sec)
   - Big5/UTF-8 編碼自動偵測

2. **建立 `app/services/mops_errors.py`**
   - `MOPSHTMLClientError`
   - `MOPSRateLimitError`
   - `MOPSDataNotFoundError`
   - `MOPSParsingError`

3. **更新 `app/services/__init__.py`**

### 實作

```python
# app/services/mops_html_client.py
import asyncio
import logging
from typing import Optional
import httpx
import pandas as pd
from io import StringIO
from app.config import settings

logger = logging.getLogger(__name__)

class MOPSHTMLClient:
    MOPS_BASE = "https://mops.twse.com.tw"
    MOPS_AJAX_BASE = f"{MOPS_BASE}/mops/web"
    
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit  # seconds between requests
        self._last_request_time = 0
        self.timeout = settings.request_timeout
    
    async def _rate_limit_wait(self):
        """Enforce rate limiting"""
        import time
        now = time.time()
        wait_time = self.rate_limit - (now - self._last_request_time)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()
    
    async def fetch_html_table(
        self,
        endpoint: str,
        params: dict,
        method: str = "POST",
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        從 MOPS 抓取 HTML 表格並轉為 DataFrame
        """
        await self._rate_limit_wait()
        
        url = f"{self.MOPS_AJAX_BASE}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            if method == "POST":
                resp = await client.post(url, data=params, headers=self._headers())
            else:
                resp = await client.get(url, params=params, headers=self._headers())
            
            resp.encoding = encoding
            return pd.read_html(StringIO(resp.text))
    
    async def fetch_static_html(
        self,
        url: str,
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        抓取靜態 HTML 頁面 (如月營收彙總表)
        """
        await self._rate_limit_wait()
        
        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            resp = await client.get(url, headers=self._headers())
            resp.encoding = encoding
            return pd.read_html(StringIO(resp.text))
    
    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.MOPS_BASE,
        }
```

### 測試

```bash
# 建立測試檔案 tests/test_mops_html_client.py
uv run pytest tests/test_mops_html_client.py -v
```

### 驗證

```bash
# 快速驗證 (Python REPL)
uv run python -c "
from app.services.mops_html_client import MOPSHTMLClient
import asyncio
client = MOPSHTMLClient()
# 測試月營收彙總表
url = 'https://mops.twse.com.tw/nas/t21/sii/t21sc03_114_12_0.html'
dfs = asyncio.run(client.fetch_static_html(url))
print(f'Found {len(dfs)} tables')
if dfs:
    print(dfs[0].head())
"
```

---

## Step 1: P0 月營收 - Service

### 任務

1. **建立 `app/services/revenue.py`**
   - `RevenueService` 類別
   - `get_monthly_revenue(year, month, stock_id=None)` 方法
   - `get_market_revenue(year, month, market='sii')` 方法
   - 使用民國年（與現有 API 保持一致）

2. **建立 `app/schemas/revenue.py`**
   - `MonthlyRevenue` Pydantic model
   - `MarketRevenueResponse` Pydantic model

### 實作

```python
# app/services/revenue.py
class RevenueService:
    """
    月營收服務
    
    URL Pattern:
    http://mops.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{type}.html
    
    Note: year 使用民國年，與現有 API 保持一致
    """
    
    MARKET_TYPES = {
        "sii": "上市",
        "otc": "上櫃", 
        "rotc": "興櫃",
        "pub": "公開發行",
    }
    
    def __init__(self, html_client: MOPSHTMLClient):
        self.client = html_client
    
    async def get_market_revenue(
        self,
        year: int,  # 民國年
        month: int,
        market: str = "sii",
        company_type: int = 0,  # 0=國內, 1=國外
    ) -> list[MonthlyRevenue]:
        url = f"https://mops.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html"
        dfs = await self.client.fetch_static_html(url)
        return self._parse_market_revenue(dfs, year, month)
    
    async def get_single_revenue(
        self,
        stock_id: str,
        year: int,  # 民國年
        month: int,
    ) -> Optional[MonthlyRevenue]:
        # 從市場資料中篩選
        pass
```

### 測試

```python
# tests/test_revenue_service.py
async def test_parse_market_revenue():
    # 使用 fixture HTML
    pass
```

### 驗證

```bash
uv run pytest tests/test_revenue_service.py -v
```

---

## Step 2: P0 月營收 - Router

### 任務

1. **建立 `app/routers/revenue.py`**
   - `GET /revenue/monthly` - 取得月營收
   - Query params: `year`, `month`, `stock_id` (optional), `market` (optional)

2. **更新 `app/main.py`**
   - 註冊 revenue router

### 實作

```python
# app/routers/revenue.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.revenue import get_revenue_service
from app.schemas.revenue import MonthlyRevenue, MarketRevenueResponse

router = APIRouter(prefix="/revenue", tags=["Operations"])

@router.get("/monthly", response_model=MarketRevenueResponse)
async def get_monthly_revenue(
    year: int = Query(..., ge=102, description="民國年 (e.g., 113)"),
    month: int = Query(..., ge=1, le=12),
    stock_id: Optional[str] = Query(None, description="股票代號，若不填則回傳全市場"),
    market: str = Query("sii", regex="^(sii|otc|rotc|pub)$"),
):
    """
    取得月營收資料
    
    - **year**: 民國年 (102 以後，IFRS 採用後)
    - **month**: 月份 (1-12)
    - **stock_id**: 股票代號 (若不填則回傳全市場)
    - **market**: 市場類型 (sii=上市, otc=上櫃, rotc=興櫃, pub=公開發行)
    """
    service = get_revenue_service()
    
    if stock_id:
        result = await service.get_single_revenue(stock_id, year, month)
        if not result:
            raise HTTPException(status_code=404, detail=f"No revenue data for {stock_id}")
        return {"data": [result]}
    else:
        data = await service.get_market_revenue(year, month, market)
        return {"data": data, "count": len(data)}
```

### 驗證

```bash
# 啟動開發伺服器
uv run uvicorn app.main:app --reload

# 測試 API
curl "http://localhost:8000/revenue/monthly?year=2024&month=12&market=sii" | jq
curl "http://localhost:8000/revenue/monthly?year=2024&month=12&stock_id=2330" | jq
```

---

## Step 3: P0 月營收 - Database

### 任務

1. **建立 `app/db/models/revenue.py`**
   - SQLAlchemy `MonthlyRevenueModel`

2. **更新 `app/db/repository.py`**
   - `RevenueRepository` 類別
   - `save_monthly_revenue()`
   - `get_monthly_revenue()`
   - `get_market_revenue()`

3. **建立 migration script**
   - `scripts/migrations/002_create_revenue_table.sql`

### 實作

```python
# app/db/models/revenue.py
from sqlalchemy import Column, Integer, String, BigInteger, Numeric, Text, DateTime, UniqueConstraint
from app.db.base import Base

class MonthlyRevenueModel(Base):
    __tablename__ = "monthly_revenue"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(String(10), nullable=False, index=True)
    company_name = Column(String(100))
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    revenue = Column(BigInteger)
    revenue_last_month = Column(BigInteger)
    revenue_last_year = Column(BigInteger)
    mom_change = Column(Numeric(10, 2))
    yoy_change = Column(Numeric(10, 2))
    accumulated_revenue = Column(BigInteger)
    accumulated_yoy = Column(Numeric(10, 2))
    comment = Column(Text)
    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'year', 'month', name='uq_revenue_stock_period'),
    )
```

### 驗證

```bash
# 執行 migration
uv run python scripts/run_migrations.py

# 測試 DB 操作
uv run pytest tests/test_revenue_db.py -v
```

---

## Step 4: P0 月營收 - Tests

### 任務

1. **建立 `tests/fixtures/revenue_sample.html`**
   - 保存真實 MOPS 月營收 HTML

2. **建立 `tests/test_revenue_service.py`**
   - 解析邏輯測試
   - Edge case 測試

3. **建立 `tests/test_revenue_router.py`**
   - API endpoint 測試
   - 參數驗證測試

### 測試案例

```python
# tests/test_revenue_service.py
import pytest
from app.services.revenue import RevenueService

class TestRevenueService:
    
    def test_parse_market_revenue_valid_html(self, sample_revenue_html):
        """測試正常 HTML 解析"""
        pass
    
    def test_url_construction(self):
        """測試 URL 建構（使用民國年）"""
        year = 113
        month = 12
        expected_url = "https://mops.twse.com.tw/nas/t21/sii/t21sc03_113_12_0.html"
        # verify URL is constructed correctly
    
    def test_handle_missing_data(self):
        """測試欄位缺失處理"""
        pass
    
    def test_handle_comment_field(self):
        """測試備註欄位解析"""
        pass


# tests/test_revenue_router.py
from fastapi.testclient import TestClient

class TestRevenueRouter:
    
    def test_get_market_revenue_success(self, client):
        """測試取得全市場營收"""
        pass
    
    def test_get_single_stock_revenue(self, client):
        """測試取得單一股票營收"""
        pass
    
    def test_invalid_year_validation(self, client):
        """測試年份驗證 (< 102)"""
        pass
    
    def test_invalid_month_validation(self, client):
        """測試月份驗證"""
        pass
```

### 驗證

```bash
uv run pytest tests/test_revenue*.py -v --cov=app/services/revenue --cov=app/routers/revenue
```

---

## Step 5-8: P1 董監事質押 (Insiders)

### Step 5: Service

```python
# app/services/insiders.py
class InsidersService:
    """
    董監事質押服務
    
    MOPS AJAX: POST https://mops.twse.com.tw/mops/web/ajax_stapap1
    """
    
    async def get_share_pledging(
        self,
        year: int,  # 民國年
        month: int,
        stock_id: Optional[str] = None,
    ) -> list[SharePledging]:
        params = {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "TYPEK": "sii",
            "year": year,  # 直接使用民國年
            "month": str(month).zfill(2),
        }
        if stock_id:
            params["co_id"] = stock_id
        
        dfs = await self.client.fetch_html_table("ajax_stapap1", params)
        return self._parse_pledging(dfs)
```

### Step 6: Router

```python
# app/routers/insiders.py
router = APIRouter(prefix="/insiders", tags=["Insider & Ownership"])

@router.get("/pledge")
async def get_share_pledging(
    year: int = Query(..., description="民國年"),
    month: int = Query(..., ge=1, le=12),
    stock_id: Optional[str] = None,
):
    """董監事質押：監控大股東斷頭風險"""
    pass
```

### Step 7-8: Database & Tests

同 Step 3-4 模式

---

## Step 9-12: P1 背書保證 (Risk - Endorsements)

### Step 9: Service

```python
# app/services/risk.py
class RiskService:
    """
    風險評估服務
    包含：背書保證、資金貸與、衍生性商品
    """
    
    async def get_endorsements(
        self,
        year: int,
        quarter: int,
        stock_id: Optional[str] = None,
    ) -> list[Endorsement]:
        """
        MOPS AJAX: POST https://mops.twse.com.tw/mops/web/ajax_t164sb02
        """
        pass
```

---

## Step 13-16: P2-P3 Features

按照相同模式實作：
- Step 13: 股利分派 (corporate.py)
- Step 14: 資金貸與 (risk.py - lending)
- Step 15: 衍生性商品 (risk.py - derivatives)
- Step 16: 資本形成 (corporate.py - capital)

---

## Step 17: 整合測試與文檔

### 任務

1. **整合測試**
   - 端到端 API 測試
   - Database 整合測試
   - Rate limiting 測試

2. **文檔更新**
   - README.md 更新
   - OpenAPI 文檔確認
   - CHANGELOG.md 完成

3. **效能測試**
   - 同時請求多個股票
   - Database 查詢效能

### 驗證

```bash
# 完整測試
uv run pytest tests/ -v --cov=app

# 啟動服務驗證 Swagger
uv run uvicorn app.main:app --reload
# 訪問 http://localhost:8000/docs
```

---

## 注意事項

### MOPS 反爬機制
- 每秒最多 1 個請求
- 設定合理的 User-Agent
- 避免短時間內大量請求同一端點

### 編碼處理
- 月營收彙總表: Big5
- AJAX API: 可能是 UTF-8，需實測

### 錯誤處理
- 網路超時: 重試 3 次
- 頁面不存在: 返回 404
- 格式變更: 記錄日誌並返回 500
