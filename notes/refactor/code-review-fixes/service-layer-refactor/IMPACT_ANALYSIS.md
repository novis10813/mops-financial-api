# Impact Analysis: Service Layer Refactor

## Files to be Modified

| File | Action | Changes |
|------|--------|---------|
| `app/services/financial.py` | MODIFY | 新增 `get_simplified_statement()` 和 `_convert_to_simplified()` |
| `app/routers/financial.py` | MODIFY | 簡化 `get_simplified_statement()`，委派給 Service |

## Files to be Created

無

## Files that May be Deleted

無

## Dependencies Between Components

```
Router (financial.py)
    ↓ calls
FinancialService
    ↓ uses
MOPSClient + XBRLParser
    ↓ returns
SimplifiedFinancialStatement (schema)
```

需要在 `financial.py` (service) 中 import `SimplifiedFinancialStatement`。

## Potential Breaking Changes

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| API 回傳格式變更 | 無 | 邏輯完全移植，不改變輸出 |
| 異常處理差異 | 低 | 統一使用 `FinancialServiceError` |

## Risks and Edge Cases

1. **Import 循環**: Schema import 通常不會造成循環依賴
2. **異常類型**: 需確保 `MOPSClientError` 被正確包裝
3. **測試覆蓋**: 現有測試可能需要調整 mock 位置
