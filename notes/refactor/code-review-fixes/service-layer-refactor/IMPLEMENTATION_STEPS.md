# Implementation Steps: Service Layer Refactor

## Checklist

### Phase 1: Service Layer
- [ ] 新增 `get_simplified_statement()` 到 `FinancialService`
- [ ] 新增 `_convert_to_simplified()` 輔助方法
- [ ] Import `SimplifiedFinancialStatement` schema

### Phase 2: Router Layer
- [ ] 簡化 `get_simplified_statement()` endpoint
- [ ] 移除內部 import 和業務邏輯
- [ ] 委派給 `FinancialService`

### Phase 3: Verification
- [ ] 手動測試 API endpoint
- [ ] 確認回傳格式未變更

---

## Step-by-Step Details

### Step 1: 新增 Service 方法

在 `app/services/financial.py` 的 `FinancialService` class 中新增：

```python
async def get_simplified_statement(
    self,
    stock_id: str,
    year: int,
    quarter: Optional[int] = None,
    statement_type: str = "income_statement",
) -> "SimplifiedFinancialStatement":
    """取得 FinMind 風格的扁平化財報"""
    from app.schemas.simplified import SimplifiedFinancialStatement, SimplifiedFinancialItem
    
    q = quarter or 4
    
    try:
        content = await self.mops_client.download_xbrl(stock_id, year, q)
    except MOPSClientError as e:
        raise FinancialServiceError(f"Failed to download XBRL: {e.message}")
    
    try:
        package = self.xbrl_parser.parse(content, stock_id, year, q)
    except XBRLParserError as e:
        raise FinancialServiceError(f"Failed to parse XBRL: {e}")
    
    return self._convert_to_simplified(package, stock_id, year, q, statement_type)
```

### Step 2: 新增轉換方法

```python
def _convert_to_simplified(
    self,
    package: XBRLPackage,
    stock_id: str,
    year: int,
    quarter: int,
    statement_type: str,
) -> "SimplifiedFinancialStatement":
    """將 XBRLPackage 轉換為 SimplifiedFinancialStatement"""
    from app.schemas.simplified import SimplifiedFinancialStatement, SimplifiedFinancialItem
    
    # 計算報表日期
    western_year = year + 1911
    quarter_month = {1: "03", 2: "06", 3: "09", 4: "12"}
    quarter_day = {1: "31", 2: "30", 3: "30", 4: "31"}
    report_date = f"{western_year}-{quarter_month[quarter]}-{quarter_day[quarter]}"
    
    # 轉換 facts
    simplified_items = []
    seen_types = set()
    
    for fact in package.facts:
        concept = fact.concept
        if concept in seen_types:
            continue
        
        if fact.value is None:
            continue
        
        parsed = parse_financial_value(fact.value)
        if parsed is None:
            continue
        
        seen_types.add(concept)
        origin_name = package.labels.get(concept, concept)
        
        simplified_items.append(SimplifiedFinancialItem(
            date=report_date,
            stock_id=stock_id,
            type=concept,
            value=float(parsed),
            origin_name=origin_name
        ))
    
    return SimplifiedFinancialStatement(
        stock_id=stock_id,
        year=year,
        quarter=quarter,
        report_date=report_date,
        statement_type=statement_type,
        items=simplified_items
    )
```

### Step 3: 簡化 Router

```python
@router.get("/{stock_id}/simplified/{statement_type}")
async def get_simplified_statement(
    stock_id: str,
    statement_type: str,
    year: int = Query(..., description="民國年"),
    quarter: Optional[int] = Query(None, ge=1, le=4),
):
    valid_types = ["income_statement", "balance_sheet", "cash_flow"]
    if statement_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid statement_type. Must be one of: {', '.join(valid_types)}"
        )
    
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
