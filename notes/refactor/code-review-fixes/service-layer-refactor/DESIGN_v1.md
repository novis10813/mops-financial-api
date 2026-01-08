# Design v1: Service Layer Refactor

## Proposed Architecture

將 `get_simplified_statement` 的業務邏輯從 Router 移至 Service 層。

```
                  [Before]                              [After]
                  
Router ─┬─ get_balance_sheet ─────→ Service      Router ─┬─ get_balance_sheet ─────→ Service
        │                                                 │
        ├─ get_income_statement ──→ Service              ├─ get_income_statement ──→ Service
        │                                                 │
        ├─ get_cash_flow ──────────→ Service              ├─ get_cash_flow ──────────→ Service
        │                                                 │
        └─ get_simplified_statement                       └─ get_simplified_statement ─→ Service
              ↓                                                 (HTTP only)
           Download XBRL                                       
           Parse XBRL
           Transform data
           (業務邏輯洩漏!)
```

## Core Changes

### 新增 `FinancialService.get_simplified_statement()`

```python
# app/services/financial.py

async def get_simplified_statement(
    self,
    stock_id: str,
    year: int,
    quarter: Optional[int] = None,
    statement_type: str = "income_statement",
) -> SimplifiedFinancialStatement:
    """
    取得 FinMind 風格的扁平化財報
    
    Args:
        stock_id: 股票代號
        year: 民國年
        quarter: 季度 (1-4)
        statement_type: 報表類型
    
    Returns:
        SimplifiedFinancialStatement
    """
    q = quarter or 4
    
    # 下載並解析
    content = await self.mops_client.download_xbrl(stock_id, year, q)
    package = self.xbrl_parser.parse(content, stock_id, year, q)
    
    # 轉換為 FinMind 格式
    return self._convert_to_simplified(package, stock_id, year, q, statement_type)


def _convert_to_simplified(
    self,
    package: XBRLPackage,
    stock_id: str,
    year: int,
    quarter: int,
    statement_type: str,
) -> SimplifiedFinancialStatement:
    """將 XBRLPackage 轉換為 SimplifiedFinancialStatement"""
    # ... 原有邏輯 ...
```

### 簡化 Router

```python
# app/routers/financial.py

@router.get("/{stock_id}/simplified/{statement_type}")
async def get_simplified_statement(
    stock_id: str,
    statement_type: str,
    year: int = Query(...),
    quarter: Optional[int] = Query(None, ge=1, le=4),
):
    # 驗證
    valid_types = ["income_statement", "balance_sheet", "cash_flow"]
    if statement_type not in valid_types:
        raise HTTPException(status_code=400, detail=...)
    
    # 委派給 Service
    service = get_financial_service()
    try:
        return await service.get_simplified_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            statement_type=statement_type,
        )
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Pros and Cons

### Pros
- ✅ 遵循 Single Responsibility Principle
- ✅ 與其他 endpoint 風格一致
- ✅ 業務邏輯可獨立測試
- ✅ 未來可加入快取支援

### Cons
- ⚠️ 需要 import `SimplifiedFinancialStatement` 到 Service
- ⚠️ 輕微增加程式碼量

## Decision

✅ **採用此設計** - 這是標準的 Extract Method + Move to Service 重構。
