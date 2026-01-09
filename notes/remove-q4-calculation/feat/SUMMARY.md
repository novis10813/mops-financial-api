# Summary: Remove Q4 Standalone Calculation

## What Was Implemented

成功移除了 API 端點中「年報 - Q3 累積」的預先計算功能。

### Changes Made

| File | Change | Lines Affected |
|------|--------|----------------|
| `app/services/financial.py` | 刪除 Q4 計算邏輯 | -57 lines |
| `app/routers/financial.py` | 更新 docstrings | ~10 lines modified |

### Code Removed

1. **`CUMULATIVE_REPORTS`** 常數 - 定義哪些報表需要 Q4 計算
2. **`_get_q4_standalone()`** 方法 - 實際執行 Q4 - Q3 計算的邏輯
3. **條件分支** - `get_financial_statement()` 中的 Q4 特殊處理

## Key Design Decisions

### Decision 1: 保留 `is_standalone` 欄位
- **決策**: 保留 schema 中的 `is_standalone` boolean 欄位
- **原因**: 作為未來擴展的 flag，不破壞 API 響應結構
- **影響**: 欄位始終為 `False`

### Decision 2: 不移除 `_build_statement_with_facts()` 方法
- **決策**: 保留此輔助方法
- **原因**: 可能有其他用途（例如自定義 fact 值的場景）
- **影響**: 無

## Known Limitations / TODOs

1. **用戶需自行計算單季**: 如果用戶需要 Q4 單季數據，需要自己下載 Q3 和 Q4 進行計算
2. **快取行為不變**: 快取仍然以 (stock_id, year, quarter, report_type) 為 key

## Test Results

```
67 passed in 44.46s
```

所有現有測試通過，無需修改測試代碼。

## Next Steps

1. ✅ 開發完成
2. ⬜ 推送到 remote: `git push origin feat/remove-q4-calculation`
3. ⬜ 執行 `/code-review` workflow（可選）
4. ⬜ 合併到 main 分支
