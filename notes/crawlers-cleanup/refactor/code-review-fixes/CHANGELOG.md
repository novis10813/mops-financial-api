# Code Review Fixes - 變更日誌

## 2026-01-09

### ✅ 主要變更

#### 重構爬蟲服務 (Refactoring Services)

- **RevenueService**:
  - 移除內部定义的 `MonthlyRevenue` 和 `MarketRevenueResponse`。
  - 改用 `app.schemas.revenue` 匯入模型。
  - 移除私有方法 `_parse_number`, `_parse_float`，改用 `app.utils.numerics.parse_financial_value`。
  - 解析迴圈增加錯誤計數與對非預期錯誤的 Warning 紀錄。
  
- **DividendService**:
  - 移除內部定义的 `DividendRecord`, `DividendSummary`, `DividendResponse`。
  - 改用 `app.schemas.dividend` 匯入模型。
  - 移除 `_parse_float`，改用 `app.utils.numerics.parse_financial_value`。
  
- **DisclosureService**:
  - 移除內部定义的 Pydantic 模型。
  - 改用 `app.schemas.disclosure` 匯入模型。
  - 重構 `_parse_int` 使用 `app.utils.numerics.parse_financial_value`。
  - 解析迴圈錯誤層級提升至 Warning。

#### 新增 Schema 檔案

- `app/schemas/revenue.py`
- `app/schemas/dividend.py`
- `app/schemas/disclosure.py`

#### 測試與路由更新

- 更新 `app/routers/revenue.py`, `dividend.py`, `disclosure.py` 的 import路徑。
- 更新 `tests/test_revenue_service.py`, `test_dividend_service.py`, `test_disclosure_service.py` 配合 Schema 移動並移除對私有解析方法的測試。

---

### 📊 統計

| 指標 | 數值 |
|------|------|
| 修改檔案數 | 9 |
| 新增檔案數 | 3 |
| 測試通過率 | 100% (34 tests passed) |

---

### 🔄 API 變更

**無破壞性變更**: API 的回應格式保持完全一致，僅內部實作結構優化。
