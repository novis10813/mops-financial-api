# 代碼審查: feat/additional-crawlers

## 1. 變更摘要
本次變更實作了多個新的財務資料爬蟲服務，包括月營收 (Revenue)、股利分派 (Dividend) 與重大資訊揭露 (Disclosure)，並建立了相應的資料庫模型與 API 端點，大幅擴展了系統的財務資料覆蓋範圍。

## 2. 重點發現 (Key Findings)

### ⚠️ High
- **代碼重複與未利用現有工具 (Code Duplication)**: 多個 Service (`RevenueService`, `DividendService`, `DisclosureService`) 重複實作了 `_parse_number` 和 `_parse_float` 等私有方法，忽視了專案中已存在且專門處理此邏輯的 `app/utils/numerics.py`。這不僅違反 DRY 原則，也造成解析邏輯不統一，應統一使用專案既有的工具庫。
- **架構違規 (Architectural Violation - Schemas)**: Pydantic 資料模型 (Schemas) 目前被定義在 `app/services/` 內的服務檔案中（例如 `MonthlyRevenue` 定義在 `revenue.py`），而非依慣例放在 `app/schemas/` 目錄下。這違反了關注點分離 (Separation of Concerns)，使得 Service 層與 API 介面定義耦合過深，應移至 `app/schemas/`。
- **錯誤處理過於隱晦 (Silent Failures)**: 在解析表格的迴圈中（例如 `_parse_revenue_tables`, `_parse_dividend_records`），使用了 `except Exception as e: logger.debug(...)` 捕捉所有異常。這會導致當 MOPS 網頁結構變更或出現未預期的資料格式時，系統只會靜默失敗（紀錄在 debug log），維運人員難以察覺資料缺失的問題。

### 💡 Medium
- **分散的外部依賴管理 (Scattered URL Management)**: MOPS 的 URL Endpoint (如 `ajax_t05st09_2`) 和參數設定散落在各個 Service 檔案中。目前的設計使得維護變得困難（例如 MOPS 改版時需修改多個檔案）。建議將所有 MOPS 相關的 URL 管理與基礎請求邏輯合併至單一的 `MOPSClient`，並透過字典或設定檔統一維護這些 Endpoints。
- **單例模式的使用 (Singleton Pattern)**: 服務層使用了全域變數 `_service` 實作單例模式。雖然目前可行，但在 FastAPI 中，使用 `Depends` 做依賴注入會更易於測試（mocking）和管理生命週期。

### ℹ️ Low
- **編碼處理不一致**: 代碼中對 Big5/UTF-8 的處理缺乏統一常數或說明。
- **型別提示完善度**: 部分 helper function 如 `_parse_int(row.iloc[1])` 的參數型別未明確標示。

## 3. 安全與合規檢查 (Security & Compliance)
- 敏感資訊: ✅ (無發現硬編碼密鑰)
- 漏洞掃描: ✅ (使用參數化查詢與 ORM，無明顯 SQL Injection 風險)

## 4. 代碼品質評分 (Quality Score)
- 可讀性: 7/10 (命名清晰，但架構層次有待加強)
- 測試覆蓋建議: 核心解析邏輯（Parsing logic）需要高覆蓋率的單元測試。
- 複雜度: 中等

## 5. 詳細建議 (Actionable Recommendations)

### 檔案: app/services/*.py (Revenue, Dividend, Disclosure)

#### [HIGH] 使用統一的數值解析工具

**問題細節**: 目前每個 Service 都自己實作了解析邏輯，忽視了 `app/utils/numerics.py`。

**建議變更**:
移除 Service 內部的 `_parse_number`, `_parse_float`，改為匯入並使用 `app.utils.numerics`。

```python
from app.utils.numerics import parse_financial_value

# 在解析邏輯中
# parse_financial_value 回傳 Decimal，比 float 更適合財務運算
# 若 Model 定義為 int/float，需做適當轉換，或建議 Model 也改用 Decimal/Numeric
revenue = parse_financial_value(row[2])
```

#### [HIGH] 移動 Schema 定義至 app/schemas/

**問題細節**: `MonthlyRevenue`, `DividendResponse`, `DisclosureResponse` 等 Pydantic Models 定義在 Service 檔案中。

**建議變更**:
1. 將這些 Class 移動到 `app/schemas/` 下的對應檔案 (如 `app/schemas/revenue.py`)。
2. 在 Service 中 import 這些 Schemas。

### 檔案: app/services/mops_html_client.py

#### [MEDIUM] 集中管理 URL Endpoints

**問題細節**: MOPS 的 URL 與參數散落在各處，缺乏統一管理。

**建議變更**:
在 `MOPSHTMLClient` 中建立統一的 Endpoint 管理機制，或擴充為功能更完整的 `MOPSClient`。

```python
class MOPSClient:
    # 集中管理 Endpoints
    ENDPOINTS = {
        'revenue_sii': 'https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{year}_{month}_{type}.html',
        'dividend': 'ajax_t05st09_2',
        'disclosure': 'ajax_t05st11',
        # ...
    }
    
    def get_endpoint_url(self, key: str, **kwargs) -> str:
        # 統一處理 URL 生成邏輯
        pass
```

### 檔案: app/services/revenue.py (範例)

#### L196-L241: [HIGH] 改善錯誤處理

**問題細節**: 使用 `logger.debug` 捕捉所有異常會隱藏真正的解析錯誤。

**建議變更**:
1. 針對預期的資料缺失（如空行）使用更精確的檢查。
2. 對於真正的解析異常，使用 `logger.warning` 甚至 `error`，或者計算失敗率。

```python
        failure_count = 0
        for idx, row in df.iterrows():
            try:
                # ... parsing logic
            except ValueError as e:
                # 資料格式錯誤，可能是預期內的雜訊
                logger.debug(f"Value error at row {idx}: {e}")
            except Exception as e:
                # 非預期的錯誤，應該被關注
                failure_count += 1
                logger.warning(f"Unexpected error parsing row {idx} in {year}/{month}: {e}", exc_info=True)
                continue
        
        if failure_count > 0:
            logger.error(f"Failed to parse {failure_count} rows in revenue table")
```
