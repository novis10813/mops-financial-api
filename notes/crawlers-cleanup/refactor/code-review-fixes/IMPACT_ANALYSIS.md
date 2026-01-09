# Code Review Fixes - Impact Analysis

## 檔案變更總覽

### 修改的檔案

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `app/services/revenue.py` | Refactor | 移除 Model 定義, 替換解析邏輯, 改善錯誤處理 |
| `app/services/dividend.py` | Refactor | 移除 Model 定義, 替換解析邏輯, 改善錯誤處理 |
| `app/services/disclosure.py` | Refactor | 移除 Model 定義, 替換解析邏輯, 改善錯誤處理 |
| `app/routers/revenue.py` | Import Fix | 更新 Schema import 路徑 |
| `app/routers/dividend.py` | Import Fix | 更新 Schema import 路徑 |
| `app/routers/disclosure.py` | Import Fix | 更新 Schema import 路徑 |

### 新增的檔案

| 檔案 | 用途 |
|------|------|
| `app/schemas/revenue.py` | 存放 Revenue 相關 Pydantic Models |
| `app/schemas/dividend.py` | 存放 Dividend 相關 Pydantic Models |
| `app/schemas/disclosure.py` | 存放 Disclosure 相關 Pydantic Models |

### 刪除的檔案

None.

---

## 依賴關係

- **Services -> Schemas**: Services 依賴新建立的 Schemas。
- **Routers -> Schemas**: Routers 改為依賴新建立的 Schemas。
- **Services -> Utils**: Services 依賴 `app.utils.numerics`。

---

## 潛在風險

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|----------|
| 數值解析行為改變 | 低 | 資料精度或格式差異 (如 Decimal vs Float) | 仔細對比 `parse_financial_value` 與原 `_parse_float` 邏輯，需確保型別轉換正確 |
| Import 循環依賴 | 低 | 應用程式無法啟動 | 確保 Schemas 只定義結構不依賴 Service 邏輯 |
| 既有測試失敗 | 中 | CI/CD 失敗 | 在修改每個檔案後執行測試，批量修正 import |

---

## 向後兼容性

- **API**: 保持完全相容。Pydantic Model 的結構未改變，只是移動了定義位置。
- **DB**: 不涉及 DB Schema 變更。
