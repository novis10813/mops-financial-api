# 代碼審查: feat/remove-q4-calculation

## 1. 變更摘要
移除 `FinancialService` 中針對 Q4 財報的「年報減去 Q3 累計」預先計算邏輯，並清理相關常數與未使用的方法，使 API 統一回傳原始財報數據。

## 2. 重點發現 (Key Findings)

### 💡 Medium
- **文件與實作不一致 (Docstring Consistency)**
  - `app/services/financial.py` 的 `get_financial_statement` docstring 仍提及 `quarter=4` 的特殊計算邏輯。
  - `app/routers/financial.py` 的 `get_income_statement` 和 `get_equity_statement` 描述中仍包含「Q4 會自動計算單季」的說明。

### ℹ️ Low
- 無。

## 3. 安全與合規檢查 (Security & Compliance)
- 敏感資訊: ✅ 通過
- 漏洞掃描: ✅ 通過 (移除複雜運算邏輯反而減少潛在錯誤)

## 4. 代碼品質評分 (Quality Score)
- **可讀性**: 9/10 (移除特殊邏輯後，流程更簡潔直觀)
- **測試覆蓋建議**: 現有測試應能通過，但建議確認是否有依賴「Q4 單季數值」的舊測試案例需要調整預期結果。
- **複雜度**: 低 (邏輯簡化)

## 5. 詳細建議 (Actionable Recommendations)

### 檔案: app/routers/financial.py

#### L75-L83: [MEDIUM] Remove stale description about Q4 calculation

**問題細節**: `get_income_statement` 的 docstring 仍聲稱 Q4 會自動計算單季，這與本次變更的實作（移除計算）矛盾。

**原始代碼**:
```python
@router.get(
    "/{stock_id}/income-statement",
    response_model=FinancialStatement,
    summary="取得綜合損益表",
    description="取得指定公司的綜合損益表（累計型，Q4 會自動計算單季）"
)
async def get_income_statement(
```

**建議代碼**:
```python
@router.get(
    "/{stock_id}/income-statement",
    response_model=FinancialStatement,
    summary="取得綜合損益表",
    description="取得指定公司的綜合損益表（累計型）"
)
async def get_income_statement(
```

#### L101-L107: [MEDIUM] Remove stale description in equity statement

**問題細節**: 同樣的問題出現在 `get_equity_statement`。

**原始代碼**:
```python
@router.get(
    "/{stock_id}/equity-statement",
    response_model=FinancialStatement,
    summary="取得權益變動表",
    description="取得指定公司的權益變動表（累計型，Q4 會自動計算單季）"
)
async def get_equity_statement(
```

**建議代碼**:
```python
@router.get(
    "/{stock_id}/equity-statement",
    response_model=FinancialStatement,
    summary="取得權益變動表",
    description="取得指定公司的權益變動表（累計型）"
)
async def get_equity_statement(
```

### 檔案: app/services/financial.py

#### L70-L75: [MEDIUM] Update get_financial_statement docstring

**問題細節**: Note 區塊仍描述已移除的行為。

**原始代碼**:
```python
        Note:
            - quarter=4 時，損益表會計算 Q4 單季 = 年報 - Q3累計
            - quarter=None 時，直接回傳年報（Q4）原始資料
            - 快取以 (stock_id, year, quarter, report_type) 為 key
```

**建議代碼**:
```python
        Note:
            - quarter=None 時，直接回傳年報（Q4）原始資料
            - 快取以 (stock_id, year, quarter, report_type) 為 key
```
