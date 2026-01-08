# Design v1: Dead Code Removal

## Decision

**直接刪除 `cached_financial.py`**，因為：
1. 它是死程式碼（從未被使用）
2. `FinancialService` 已經包含完整的快取邏輯

## 驗證現有邏輯正確性

### `FinancialService.get_financial_statement()` 流程

```python
async def get_financial_statement(..., use_cache: bool = True):
    # 1. 先檢查資料庫快取
    if use_cache:
        cached = await repo.get_report(stock_id, year, quarter, report_type)
        if cached:
            return cached  # Cache HIT
    
    # 2. Cache MISS → 從 MOPS 下載
    content = await self.mops_client.download_xbrl(...)
    package = self.xbrl_parser.parse(...)
    statement = self._build_statement(package, report_type)
    
    # 3. 儲存到資料庫
    await repo.save_report(statement)
    
    return statement
```

**這完全符合需求：DB First → MOPS Fallback → Save to DB** ✅

## 變更清單

### 要刪除的檔案
- `app/services/cached_financial.py`

### 要檢查的檔案
- `app/services/__init__.py` - 如果有 export
- 其他可能 import 的地方

## Pros and Cons

### Pros
- ✅ 消除死程式碼
- ✅ 消除邏輯重複
- ✅ 減少維護負擔
- ✅ 程式碼更清晰

### Cons
- ⚠️ 無（這是純粹的清理）
