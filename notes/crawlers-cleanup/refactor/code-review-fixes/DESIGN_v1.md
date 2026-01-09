# Code Review Fixes - 設計方案 v1

## 設計原則

1.  **DRY (Don't Repeat Yourself)**: 移除重複的解析邏輯，使用共用工具。
2.  **Separation of Concerns**: 資料定義 (Schemas) 與業務邏輯 (Services) 分離。
3.  **Fail Loudly (for unexpected errors)**: 預期外的錯誤應該被看見，而非被吞沒。

---

## 方案

### 概覽

本方案將重新組織 `app/services` 中的爬蟲模組，將其中的 Pydantic 模型移出至 `app/schemas`，並將內部的數值解析邏輯替換為 `app.utils.numerics` 的調用。同時增強錯誤處理機制。

### 詳細設計

#### 1. Schema 重組
建立以下檔案：
- `app/schemas/revenue.py`: 存放 `MonthlyRevenue` 等模型。
- `app/schemas/dividend.py`: 存放 `DividendResponse` 等模型。
- `app/schemas/disclosure.py`: 存放 `DisclosureResponse` 等模型。

#### 2. Service 重構
以 `RevenueService` 為例：
- 移除 `_parse_number`, `_parse_float`。
- Import `from app.utils.numerics import parse_financial_value`。
- 修改 `_parse_revenue_tables` 使用 `parse_financial_value`，需注意 `parse_financial_value` 回傳 `Decimal`，若 Model 欄位為 `float` 需做轉換，或考慮將 Model 欄位改為 `Decimal` (建議與現有 DB model 保持一致，若 DB 是 float/numeric 則轉型)。

#### 3. 錯誤處理優化
```python
failure_count = 0
for idx, row in df.iterrows():
    try:
        # parsing logic
    except ValueError as e:
        # 預期的資料格式問題
        logger.debug(f"Row {idx} skip: {e}")
    except Exception as e:
        # 非預期錯誤
        failure_count += 1
        logger.error(f"Unexpected error at row {idx}: {e}", exc_info=True)

if failure_count > 0:
    logger.warning(f"Batch completed with {failure_count} failures")
```

---

## 優缺點

| 優點 | 缺點 |
|------|------|
| 提高代碼復用率，減少 bug 機會 | 需要修改多個檔案，並手動驗證所有 import |
| 架構更清晰，符合專案慣例 | 若 `parse_financial_value` 行為與原實作有細微差異，可能導致資料邊緣案例變化 |
| 錯誤更容易被發現 | |

---

## 替代方案

- **原地重構**: 不移動 Schemas，只修邏輯。
  - *缺點*: 仍違反架構原則，未來還是要改。
- **全面重寫**: 建立一個通用的 `FinancialTableParser`。
  - *缺點*: 範圍過大，風險高，非本次目標。
