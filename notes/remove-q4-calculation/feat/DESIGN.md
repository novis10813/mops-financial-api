# Design: Remove Q4 Standalone Calculation

## Architecture Overview

此修改為「簡化」型重構，主要移除現有功能而非新增。

### Current Flow (Before)

```
API Request (quarter=4)
    │
    ▼
get_financial_statement()
    │
    ├─► if quarter=4 && cumulative_report:
    │       │
    │       ▼
    │   _get_q4_standalone()
    │       │ (Download Q3 & Calculate)
    │       ▼
    │   Return: Q4 - Q3
    │
    └─► else:
            │
            ▼
        _build_statement()
            │
            ▼
        Return: Raw Data
```

### Target Flow (After)

```
API Request (any quarter)
    │
    ▼
get_financial_statement()
    │
    ▼
_build_statement()
    │
    ▼
Return: Raw Data
```

## Component Changes

### 1. `app/services/financial.py`

| Element | Action | Description |
|---------|--------|-------------|
| `CUMULATIVE_REPORTS` | DELETE | 移除累計型報表列表常數 |
| `_get_q4_standalone()` | DELETE | 移除 Q4 單季計算方法（約 40 行） |
| `get_financial_statement()` | MODIFY | 移除 L120-126 的條件分支 |

### 2. `app/routers/financial.py`

| Endpoint | Action | Description |
|----------|--------|-------------|
| `get_income_statement()` | MODIFY | 更新 docstring，移除 Q4 計算說明 |
| `get_equity_statement()` | MODIFY | 更新 docstring，移除 Q4 計算說明 |

### 3. `app/schemas/financial.py` (評估)

| Field | Decision | Reason |
|-------|----------|--------|
| `is_standalone` | KEEP | 可作為未來擴展的 flag，目前預設值為 False 即可 |

## Data Structures

無需改變現有資料結構。`FinancialStatement` schema 保持不變。

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| 破壞現有 API 使用者 | Low | 回傳格式不變，只是數據來源變成原始值 |
| 測試失敗 | Low | 預期簡化後測試應該更容易通過 |

## Rollback Strategy

如需回滾，只需 `git revert` 此 commit 即可恢復 Q4 計算功能。
