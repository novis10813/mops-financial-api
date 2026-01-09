# MOPS Financial API - Additional Crawlers

本次新增的 API 端點，用於從公開資訊觀測站 (MOPS) 獲取額外的財務資訊。

## 🎯 功能概覽

| 功能 | Endpoint | 說明 | MOPS 來源 |
|------|----------|------|-----------|
| 月營收 | `/api/v1/revenue/monthly` | 全市場和單一公司月營收 | Static HTML |
| 董監事質押 | `/api/v1/insiders/pledge` | 董監事持股與質押比例 | ajax_stapap1 |
| 股利分派 | `/api/v1/dividend` | 現金/股票股利，支援季配息 | ajax_t05st09_2 |
| 重大揭露 | `/api/v1/disclosure` | 資金貸放 + 背書保證 | ajax_t05st11 |

---

## 📊 月營收 (Revenue)

### GET `/api/v1/revenue/monthly`

取得全市場的月營收資料。

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | int | ✅ | 民國年 (102-200) |
| `month` | int | ✅ | 月份 (1-12) |
| `stock_id` | string | ❌ | 股票代號，若不填則回傳全市場 |
| `market` | string | ❌ | 市場類型: `sii`=上市, `otc`=上櫃 |

**Response Example:**

```json
{
  "year": 113,
  "month": 12,
  "market": "sii",
  "count": 973,
  "data": [
    {
      "stock_id": "2330",
      "company_name": "台積電",
      "year": 113,
      "month": 12,
      "revenue": 278163107,
      "revenue_last_month": 276058358,
      "revenue_last_year": 176299866,
      "mom_change": 0.76,
      "yoy_change": 57.77,
      "accumulated_revenue": 2894307699,
      "accumulated_last_year": 2161735841,
      "accumulated_yoy_change": 33.88,
      "comment": "因先進製程產品需求增加所致"
    }
  ]
}
```

### GET `/api/v1/revenue/monthly/{stock_id}`

取得單一公司的月營收資料。

---

## 🏛️ 董監事質押 (Insiders)

### GET `/api/v1/insiders/pledge/{stock_id}`

取得董監事持股與質押資料。

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | int | ✅ | 民國年 |
| `month` | int | ✅ | 月份 |
| `market` | string | ❌ | `sii` 或 `otc` |

**Response Example:**

```json
{
  "stock_id": "2330",
  "company_name": "台灣積體電路製造股份有限公司",
  "year": 113,
  "month": 12,
  "summary": {
    "total_shares": 1689702315,
    "total_pledged": 1600000,
    "total_pledge_ratio": 0.09
  },
  "details": [
    {
      "title": "董事長",
      "name": "魏哲家",
      "current_shares": 6392834,
      "pledged_shares": 1600000,
      "pledge_ratio": 25.02
    }
  ]
}
```

**風險評估:**
- `pledge_ratio > 50%`: 高質押比例，有斷頭風險
- `pledge_ratio > 80%`: 極高風險

---

## 💰 股利分派 (Dividend)

### GET `/api/v1/dividend/{stock_id}`

取得股利分派記錄，支援季配息公司（如台積電）。

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year_start` | int | ✅ | 起始年度 (民國年) |
| `year_end` | int | ❌ | 結束年度 |
| `query_type` | int | ❌ | 1=董事會決議年度, 2=股利所屬年度 |

**Response Example:**

```json
{
  "stock_id": "2330",
  "company_name": "台積電",
  "year_start": 112,
  "year_end": 112,
  "count": 4,
  "records": [
    {
      "year": 112,
      "quarter": 4,
      "cash_dividend": 3.4998,
      "stock_dividend": 0,
      "board_resolution_date": "113/02/06"
    },
    {
      "year": 112,
      "quarter": 3,
      "cash_dividend": 3.4998,
      "stock_dividend": 0
    },
    {
      "year": 112,
      "quarter": 2,
      "cash_dividend": 3.0,
      "stock_dividend": 0
    },
    {
      "year": 112,
      "quarter": 1,
      "cash_dividend": 3.0,
      "stock_dividend": 0
    }
  ]
}
```

### GET `/api/v1/dividend/{stock_id}/summary`

取得年度股利彙總。

```json
{
  "stock_id": "2330",
  "year": 112,
  "total_cash_dividend": 13.0,
  "total_stock_dividend": 0,
  "total_dividend": 13.0
}
```

---

## 📋 重大揭露 (Disclosure)

### GET `/api/v1/disclosure/{stock_id}`

取得資金貸放與背書保證資訊。

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | int | ✅ | 民國年 |
| `month` | int | ✅ | 月份 |
| `market` | string | ❌ | `sii` 或 `otc` |

**Response Example:**

```json
{
  "stock_id": "2317",
  "company_name": "鴻海",
  "year": 112,
  "month": 12,
  "funds_lending": [
    {
      "entity": "本公司",
      "has_balance": true,
      "current_month": 5000000,
      "previous_month": 5000000,
      "max_limit": 593999872
    },
    {
      "entity": "子公司",
      "has_balance": true,
      "current_month": 110002782,
      "max_limit": 13102874199
    }
  ],
  "endorsement_guarantee": [
    {
      "entity": "本公司",
      "has_balance": true,
      "monthly_change": -3508687,
      "accumulated_balance": 198915488,
      "max_limit": 1484999679
    }
  ],
  "cross_company": {
    "parent_to_subsidiary": 198915488,
    "subsidiary_to_parent": 0
  },
  "china_guarantee": [
    {
      "entity": "子公司",
      "accumulated_balance": 7359563
    }
  ]
}
```

**風險評估:**
- 背書保證餘額接近限額：流動性風險
- 大陸地區占比高：政治風險
- 本公司對子公司背書：關係人交易

---

## 🔧 技術說明

### MOPS 端點對照

| 功能 | MOPS Endpoint | 方法 |
|------|---------------|------|
| 月營收 | `/nas/t21/{market}/t21sc03_{year}_{month}_{type}.html` | GET |
| 董監事質押 | `/mops/web/ajax_stapap1` | POST |
| 股利分派 | `/mops/web/ajax_t05st09_2` | POST |
| 資金貸放/背書保證 | `/mops/web/ajax_t05st11` | POST |

### 年度格式

所有 API 使用**民國年 (ROC Year)**：
- 民國 113 年 = 西元 2024 年
- 民國 112 年 = 西元 2023 年

### Rate Limiting

內建 1 秒間隔的 rate limiting，避免對 MOPS 造成過大負載。

---

## 📈 使用場景

### 1. 殖利率計算

```python
# 取得年度股利
dividend = await service.get_annual_summary("2330", 112)
# 假設股價 500 元
yield_rate = dividend.total_cash_dividend / 500 * 100
# ~2.6%
```

### 2. 質押風險監控

```python
# 取得質押資料
pledging = await service.get_share_pledging("2330", 113, 12)
# 找出高質押比例人員
high_risk = [d for d in pledging.details if d.pledge_ratio > 50]
```

### 3. 營收成長追蹤

```python
# 取得月營收
revenue = await service.get_single_revenue("2330", 113, 12)
# YoY 成長率
yoy_growth = revenue.yoy_change  # 57.77%
```

---

## 📝 更新日誌

- **2024-01-09**: 新增月營收、董監事質押、股利分派、資金貸放/背書保證 API
