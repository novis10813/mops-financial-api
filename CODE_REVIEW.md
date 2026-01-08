# 代碼審查: mops-financial-api (Manual Review)

## 1. 變更摘要
這是一份針對現有代碼庫的手動審查報告。主要關注代碼結構、潛在的安全風險、重複邏輯以及架構設計問題。

整體而言，核心功能（XBRL 解析、財報建構）已經實作，但存在明顯的代碼重複（DRY 違規）、安全隱患（SSL 校驗關閉）以及業務邏輯洩漏到 Router 層的問題。

## 2. 重點發現 (Key Findings)

### 🚨 Critical
- **[Security] SSL 憑證驗證被禁用**: 在 `app/services/taxonomy_manager.py` 中，使用 `httpx.AsyncClient(verify=False)` 進行網路請求。這會使應用程式容易受到中間人攻擊 (MITM)。
- **[Logic] 數值解析邏輯重複且脆弱**: 字串轉數值 (移除逗號、處理小數點) 的邏輯被複製貼上在多個地方 (`xbrl_parser.py`, `financial.py`, `routers/financial.py`)。任何修改都需要同步更新所有位置，極易出錯。

### ⚠️ High
- **[Architecture] 業務邏輯洩漏至 Router**: `app/routers/financial.py` 中的 `get_simplified_statement` 函式直接執行了下載、解析和資料轉換邏輯。這應該被封裝在 `FinancialService` 中，Router 應僅負責 HTTP 請求處理。
- **[Stability] 依賴網頁爬蟲取得 Taxonomy**: `TaxonomyManager` 使用 Regex 解析 MOPS 網頁 (`_scrape_taxonomy_list`)。若 MOPS 網頁改版，此功能將直接失效。應增加更強健的錯誤處理或配置檔機制。

### 💡 Medium
- **[Readability] `xbrl_parser.py` 職責過重**: 該檔案同時包含了 ZIP 解壓、iXBRL HTML 解析 (LXML & Arelle)、以及 Taxonomy 連結庫 (Linkbase) 的解析邏輯。建議拆分為獨立的模組 (e.g., `parsers/arelle.py`, `parsers/lxml.py`)。
- **[Convention] Router 內部的 import**: `get_simplified_statement` 內部進行了大量 import (`get_mops_client`, `get_xbrl_parser` 等)。除非是為了避免循環依賴且無解，否則應移至檔案頂部。

### ℹ️ Low
- **[Global State] 單例模式實作**: 使用全域變數 (`global _taxonomy_manager`) 實作單例。雖然可用，但在測試時可能較難 mock。建議使用依賴注入 (Dependency Injection) 或 FastAPI 的 `Depends` 機制。

## 3. 安全與合規檢查 (Security & Compliance)
- 敏感資訊: 未發現硬編碼的金鑰 (良好，config 使用環境變數)。
- 漏洞掃描: 發現 `verify=False` (CVE CWE-295)。

## 4. 代碼品質評分 (Quality Score)
- 可讀性: 7/10 (變數命名清晰，有 docstring)
- 架構設計: 6/10 (Router 與 Service 界線模糊)
- 測試覆蓋建議: 需針對 `FinancialService.get_financial_statement` 和 Q4 計算邏輯加強單元測試。

## 5. 詳細建議 (Actionable Recommendations)

### 檔案: app/services/taxonomy_manager.py

#### L117: [CRITICAL] 啟用 SSL 驗證

**問題細節**: 關閉 SSL 驗證會導致安全風險。若 MOPS 憑證有問題應將憑證加入信任清單，而非全域關閉。

**原始代碼**:
```python
async with httpx.AsyncClient(verify=False) as client:
```

**建議代碼**:
```python
# 建議設定 CA bundle path 或預設開啟驗證
# 若必須暫時繞過，應加上明確警告並記錄 issue
async with httpx.AsyncClient(verify=True) as client: 
# 或 verify=settings.ssl_ca_bundle_path
```

### 檔案: app/routers/financial.py

#### L133: [HIGH] 重構 Simplified 報表邏輯

**問題細節**: Router 不應包含下載與解析邏輯。

**建議**: 將邏輯移至 `FinancialService`。

**原始代碼**: (Router 內直接透過 Client 下載並 Parse)
```python
@router.get(...)
async def get_simplified_statement(...):
    ...
    content = await client.download_xbrl(...)
    package = parser.parse(...)
    ...
```

**建議代碼**:
```python
# In Router
@router.get(...)
async def get_simplified_statement(...):
    service = get_financial_service()
    return await service.get_simplified_statement(stock_id, statement_type, year, quarter)

# In FinancialService
async def get_simplified_statement(self, ...):
    # 實作原有的下載與轉換邏輯
    pass
```

### 專案通用建議: 建立 Utils

**問題細節**: 數值清理邏輯重複。

**建議**: 建立 `app/utils/numerics.py`

```python
def parse_financial_value(value_str: str) -> Optional[Decimal]:
    if not value_str:
        return None
    cleaned = value_str.replace(",", "").strip()
    if not cleaned or cleaned in ("-", ""):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
```
所有解析邏輯 (`xbrl_parser.py`, `financial.py`) 統一呼叫此函式。
