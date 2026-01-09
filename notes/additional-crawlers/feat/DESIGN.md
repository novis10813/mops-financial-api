# Additional MOPS Crawlers - Design Document

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Application                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Routers (4 Domains)                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │   revenue    │ │     risk     │ │   insiders   │ │  corporate   │   │
│  │ (Operations) │ │    (Risk)    │ │ (Ownership)  │ │  (Actions)   │   │
│  │   月營收     │ │背書/資金/衍生│ │  董監質押    │ │ 股利/資本    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  Services                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    MOPS HTML Client (新增)                        │   │
│  │  - 處理 HTML 表格爬取                                             │   │
│  │  - Big5 編碼處理                                                  │   │
│  │  - Rate limiting                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐│
│  │  Revenue   │ │Endorsement │ │  Insiders  │ │  Dividend  │ │Capital ││
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │ │Service ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────┘│
├─────────────────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL)                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  monthly_revenue | endorsements | share_pledging | dividends     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Three Critical Design Points

### 1. 時間格式統一 (Year Transformation)

**問題**: MOPS 使用民國年 (如 112)，但量化分析系統都用西元年 (如 2023)

**設計決策**:
- **API 輸入/輸出**: 永遠使用**西元年**
- **內部轉換**: Router/Service 負責 `mops_year = year - 1911`
- **資料庫儲存**: 使用**西元年**

```python
# API 使用者永遠不需要知道民國年
@router.get("/monthly")
async def get_monthly_revenue(
    year: int = Query(..., description="西元年 (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12),
):
    roc_year = year - 1911  # 內部轉換
    # ...
```

### 2. 資料更新觸發 (Read vs. Force Update)

**設計決策**: 分離讀取和更新操作

| 操作 | HTTP 方法 | 端點 | 說明 |
|------|-----------|------|------|
| 讀取資料 | GET | `/revenue/monthly` | 從 DB 撈資料，毫秒級回應 |
| 強制更新 | POST | `/spider/trigger/revenue` | 背景執行爬蟲，需要權限 |

**權限控制**:
- 一般使用者: 只能 GET
- Admin: 可以 POST trigger

### 3. 全市場 vs 個股 (Bulk vs Specific)

**MOPS 特性**: 月營收可一次下載全市場 CSV

**設計決策**:
- `stock_id` 為空: 回傳該月/該季的**全市場清單** (適合 Screening/選股)
- `stock_id` 有值: 回傳該股的**歷史序列** (適合 Charting/畫圖)

```python
@router.get("/monthly")
async def get_monthly_revenue(
    year: int,
    month: int,
    stock_id: Optional[str] = Query(None, description="若不填則回傳全市場")
):
    if stock_id:
        return get_single_stock_revenue(stock_id, year, month)
    else:
        return get_market_revenue(year, month)
```

---

## Router 組織 (4 Domains)

```
app/routers/
├── financial.py     # 現有 - XBRL 財報
├── revenue.py       # 新增 - 營運面 (Operations)
├── risk.py          # 新增 - 風險面 (Risk Management)
├── insiders.py      # 新增 - 籌碼與治理面 (Insider & Ownership)
└── corporate.py     # 新增 - 公司決策面 (Corporate Actions)
```

---

## Component Breakdown

### 1. MOPS HTML Client (`app/services/mops_html_client.py`)

**職責**: 通用的 MOPS HTML 表格爬取客戶端

```python
class MOPSHTMLClient:
    """
    MOPS HTML 表格爬取客戶端
    - 與現有 MOPSClient (XBRL) 分離
    - 處理 Big5 編碼
    - 實作 rate limiting
    """
    
    MOPS_BASE = "https://mops.twse.com.tw"
    MOPS_AJAX_BASE = f"{MOPS_BASE}/mops/web"
    
    async def fetch_html_table(
        self,
        endpoint: str,
        params: dict,
        method: str = "POST",
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        從 MOPS 抓取 HTML 表格並轉為 DataFrame
        
        Args:
            endpoint: MOPS 端點 (e.g., "ajax_t21sb01")
            params: 請求參數
            method: HTTP 方法
            encoding: 編碼 (big5 或 utf-8)
        
        Returns:
            解析後的 DataFrame 列表
        """
        pass
    
    async def _rate_limit(self):
        """實作 rate limiting，避免 IP ban"""
        pass
```

**設計決策**:
- 與現有 `MOPSClient` 分離，因為 XBRL 和 HTML 爬取邏輯差異大
- 使用 `pd.read_html()` 解析表格，這是最穩定的方式
- 內建 rate limiting (預設 1 請求/秒)

---

### 2. Revenue Service (`app/services/revenue.py`)

**職責**: 月營收資料服務

**MOPS URL 結構**:
```
# 彙總表 (所有公司某月營收)
http://mops.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{type}.html
# market: sii (上市), otc (上櫃), rotc (興櫃), pub (公開發行)
# type: 0 (國內), 1 (國外)

# 個股查詢 (AJAX)
POST https://mops.twse.com.tw/mops/web/ajax_t21sb01
```

**資料模型**:
```python
class MonthlyRevenue(BaseModel):
    stock_id: str           # 股票代號
    company_name: str       # 公司名稱
    year: int               # 西元年 (API 層)
    month: int              # 月份
    revenue: int            # 本月營收 (千元)
    revenue_last_month: Optional[int]  # 上月營收
    revenue_last_year: Optional[int]   # 去年同月營收
    mom_change: Optional[float]        # MoM 增減率 (%)
    yoy_change: Optional[float]        # YoY 增減率 (%)
    accumulated_revenue: Optional[int] # 累計營收
    accumulated_yoy: Optional[float]   # 累計 YoY (%)
    comment: Optional[str]             # 備註
```

---

### 3. Risk Service (`app/services/risk.py`)

**職責**: 背書保證、資金貸與、衍生性商品服務

**MOPS URL**:
```
POST https://mops.twse.com.tw/mops/web/ajax_t164sb02  # 背書保證
POST https://mops.twse.com.tw/mops/web/ajax_t164sb01  # 資金貸與
POST https://mops.twse.com.tw/mops/web/ajax_t164sb03  # 衍生性商品
```

**資料模型**:
```python
class Endorsement(BaseModel):
    stock_id: str
    year: int               # 西元年
    quarter: int
    endorsed_company: str    # 被背書保證對象
    relationship: str        # 關係
    limit_amount: int        # 限額
    outstanding_amount: int  # 餘額
    collateral: Optional[str]  # 擔保品
    net_worth_ratio: float   # 佔淨值比率 (%)

class LendingFunds(BaseModel):
    stock_id: str
    year: int
    quarter: int
    borrower: str            # 借款對象
    relationship: str        # 關係
    outstanding_amount: int  # 餘額
    interest_rate: Optional[float]  # 利率
    purpose: Optional[str]   # 用途

class DerivativePosition(BaseModel):
    stock_id: str
    year: int
    quarter: int
    instrument_type: str     # 商品類型 (期貨、選擇權、遠期外匯等)
    contract_amount: int     # 契約金額
    fair_value: int          # 公平價值
    unrealized_gain_loss: int  # 未實現損益
    purpose: str             # 目的 (避險/交易)
```

---

### 4. Insiders Service (`app/services/insiders.py`)

**職責**: 董監事質押服務

**MOPS URL**:
```
POST https://mops.twse.com.tw/mops/web/ajax_stapap1
```

**資料模型**:
```python
class SharePledging(BaseModel):
    stock_id: str
    report_date: date        # 申報日期
    title: str               # 職稱 (董事長、董事等)
    name: str                # 姓名
    shares_held: int         # 持股張數
    shares_pledged: int      # 質押張數
    pledge_ratio: float      # 質押比率 (%)
    pledgee: Optional[str]   # 質權人 (銀行)
```

---

### 5. Corporate Service (`app/services/corporate.py`)

**職責**: 股利分派與資本形成服務

**MOPS URL**:
```
POST https://mops.twse.com.tw/mops/web/ajax_t05st09_2  # 股利分派
POST https://mops.twse.com.tw/mops/web/ajax_t05st01    # 歷年股本形成過程
```

**資料模型**:
```python
class DividendPolicy(BaseModel):
    stock_id: str
    year: int                # 西元年 (發放年度)
    cash_dividend: float     # 現金股利 (元)
    stock_dividend: float    # 股票股利 (元)
    total_dividend: float    # 合計股利
    ex_dividend_date: Optional[date]  # 除息日
    ex_rights_date: Optional[date]    # 除權日
    payment_date: Optional[date]      # 發放日
    eps: Optional[float]     # 每股盈餘
    payout_ratio: Optional[float]     # 盈餘發放率 (%)

class CapitalChange(BaseModel):
    stock_id: str
    change_date: date
    change_type: str         # 類型 (現金增資/私募/可轉債轉換/減資...)
    shares_before: int       # 變動前股數
    shares_after: int        # 變動後股數
    shares_changed: int      # 變動股數
    price_per_share: Optional[float]  # 每股發行價格
    description: Optional[str]
```

---

## API Design

### Router Endpoints

#### A. Revenue Router (`/revenue`) - Operations

```python
router = APIRouter(prefix="/revenue", tags=["Operations"])

@router.get("/monthly")
async def get_monthly_revenue(
    year: int = Query(..., description="西元年 (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12),
    stock_id: Optional[str] = Query(None, description="若不填則回傳全市場")
):
    """取得特定月份的營收，包含 MoM, YoY"""
    pass
```

#### B. Risk Router (`/risk`) - Risk Management

```python
router = APIRouter(prefix="/risk", tags=["Risk Management"])

@router.get("/endorsements")
async def get_endorsements(
    year: int,
    season: int = Query(..., ge=1, le=4, alias="quarter"),
    stock_id: Optional[str] = None
):
    """背書保證：對單一企業背書保證金額、佔淨值比率"""
    pass

@router.get("/lending")
async def get_lending_funds(
    year: int,
    season: int = Query(..., ge=1, le=4, alias="quarter"),
    stock_id: Optional[str] = None
):
    """資金貸與：資金貸與餘額"""
    pass

@router.get("/derivatives")
async def get_derivatives(
    year: int,
    season: int = Query(..., ge=1, le=4, alias="quarter"),
    stock_id: Optional[str] = None
):
    """衍生性商品：未實現損益、契約總金額"""
    pass
```

#### C. Insiders Router (`/insiders`) - Insider & Ownership

```python
router = APIRouter(prefix="/insiders", tags=["Insider & Ownership"])

@router.get("/pledge")
async def get_share_pledging(
    year: int,
    month: int,
    stock_id: Optional[str] = None
):
    """董監事質押：監控大股東斷頭風險"""
    pass
```

#### D. Corporate Router (`/corporate`) - Corporate Actions

```python
router = APIRouter(prefix="/corporate", tags=["Corporate Actions"])

@router.get("/dividends")
async def get_dividend_policy(
    year: int,
    stock_id: Optional[str] = None
):
    """股利分派：計算殖利率 (Yield)、除權息日"""
    pass

@router.get("/capital-formation")
async def get_capital_changes(
    year: int,
    stock_id: Optional[str] = None
):
    """資本形成 (增資/減資/私募)：判斷股本稀釋程度"""
    pass
```

---

## Database Schema

### New Tables

```sql
-- 月營收
CREATE TABLE monthly_revenue (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    company_name VARCHAR(100),
    year INT NOT NULL,           -- 西元年
    month INT NOT NULL,
    revenue BIGINT,
    revenue_last_month BIGINT,
    revenue_last_year BIGINT,
    mom_change DECIMAL(10, 2),
    yoy_change DECIMAL(10, 2),
    accumulated_revenue BIGINT,
    accumulated_yoy DECIMAL(10, 2),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, year, month)
);

-- 背書保證
CREATE TABLE endorsements (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    endorsed_company VARCHAR(100),
    relationship VARCHAR(50),
    limit_amount BIGINT,
    outstanding_amount BIGINT,
    collateral TEXT,
    net_worth_ratio DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, year, quarter, endorsed_company)
);

-- 資金貸與
CREATE TABLE lending_funds (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    borrower VARCHAR(100),
    relationship VARCHAR(50),
    outstanding_amount BIGINT,
    interest_rate DECIMAL(5, 2),
    purpose TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, year, quarter, borrower)
);

-- 董監事質押
CREATE TABLE share_pledging (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    title VARCHAR(50),
    name VARCHAR(50),
    shares_held BIGINT,
    shares_pledged BIGINT,
    pledge_ratio DECIMAL(5, 2),
    pledgee VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, report_date, name)
);

-- 股利分派
CREATE TABLE dividends (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    year INT NOT NULL,
    cash_dividend DECIMAL(10, 4),
    stock_dividend DECIMAL(10, 4),
    total_dividend DECIMAL(10, 4),
    ex_dividend_date DATE,
    ex_rights_date DATE,
    payment_date DATE,
    eps DECIMAL(10, 4),
    payout_ratio DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, year)
);

-- 衍生性商品
CREATE TABLE derivatives (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    instrument_type VARCHAR(50),
    contract_amount BIGINT,
    fair_value BIGINT,
    unrealized_gain_loss BIGINT,
    purpose VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 資本變動
CREATE TABLE capital_changes (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    change_date DATE NOT NULL,
    change_type VARCHAR(50),
    shares_before BIGINT,
    shares_after BIGINT,
    shares_changed BIGINT,
    price_per_share DECIMAL(10, 2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_monthly_revenue_stock ON monthly_revenue(stock_id);
CREATE INDEX idx_monthly_revenue_date ON monthly_revenue(year, month);
CREATE INDEX idx_endorsements_stock ON endorsements(stock_id);
CREATE INDEX idx_lending_funds_stock ON lending_funds(stock_id);
CREATE INDEX idx_share_pledging_stock ON share_pledging(stock_id);
CREATE INDEX idx_dividends_stock ON dividends(stock_id);
CREATE INDEX idx_derivatives_stock ON derivatives(stock_id);
CREATE INDEX idx_capital_changes_stock ON capital_changes(stock_id);
```

---

## Implementation Priority

考量投資價值和技術難度，建議實作順序：

| Priority | Feature | Router | 投資價值 | 技術難度 | 說明 |
|----------|---------|--------|----------|----------|------|
| 🔥 P0 | 月營收 | revenue | ⭐⭐⭐⭐⭐ | ⭐⭐ | 最重要的領先指標，URL 規律清楚 |
| 🔴 P1 | 董監事質押 | insiders | ⭐⭐⭐⭐ | ⭐⭐ | 風控關鍵，AJAX 請求簡單 |
| 🔴 P1 | 背書保證 | risk | ⭐⭐⭐⭐ | ⭐⭐⭐ | 地雷指標，表格較複雜 |
| 🟡 P2 | 股利分派 | corporate | ⭐⭐⭐⭐ | ⭐⭐ | 殖利率計算必備 |
| 🟡 P2 | 資金貸與 | risk | ⭐⭐⭐ | ⭐⭐⭐ | 與背書保證類似 |
| 🟢 P3 | 衍生性商品 | risk | ⭐⭐⭐ | ⭐⭐⭐ | 特定產業才需要 |
| 🟢 P3 | 資本形成 | corporate | ⭐⭐⭐ | ⭐⭐⭐⭐ | 涉及多種類型，較複雜 |

---

## Error Handling

```python
class MOPSHTMLClientError(Exception):
    """MOPS HTML 爬取錯誤的基類"""
    pass

class MOPSRateLimitError(MOPSHTMLClientError):
    """被 MOPS 限制請求"""
    pass

class MOPSDataNotFoundError(MOPSHTMLClientError):
    """查無資料 (可能是股票代號錯誤或該期資料未公布)"""
    pass

class MOPSParsingError(MOPSHTMLClientError):
    """HTML 解析失敗 (可能是 MOPS 表格格式變更)"""
    pass
```

---

## Testing Strategy

### Unit Tests
- 各 Service 的資料解析邏輯 (使用 mock HTML)
- Pydantic model validation
- Error handling

### Integration Tests
- 實際呼叫 MOPS (with rate limiting)
- Database CRUD operations
- API endpoint tests

### Test Data
- 保存真實 MOPS 回應的 HTML 作為 fixtures
- 使用 `responses` 或 `respx` mock HTTP 請求

---

## Open Questions (Resolved)

1. ✅ **Router 結構**: 確認使用 4 Routers (revenue, risk, insiders, corporate)
2. ✅ **時間格式**: API 使用西元年，內部轉換民國年
3. ✅ **查詢模式**: 支援全市場和個股兩種模式

### Remaining Questions

1. **快取策略**: 月營收每月更新，要設定多長的 TTL？
   - 建議：當月資料 TTL = 1天，歷史資料 TTL = 永久

2. **編碼問題**: 部分 MOPS 頁面混用 Big5 和 UTF-8，需要實測確認

3. **反爬機制**: MOPS 是否有 CAPTCHA？需要實測

4. **資料完整性**: 部分欄位可能為空或格式不一致，需要彈性處理
