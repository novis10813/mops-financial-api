# Problem Definition: Service Layer Refactor

## Background

在 `CODE_REVIEW.md` 中發現的 **High** 問題：業務邏輯洩漏至 Router。

`app/routers/financial.py` 中的 `get_simplified_statement` 函式（L133-237）直接執行了：
- MOPS 下載邏輯
- XBRL 解析邏輯
- 資料轉換邏輯

這違反了 **Single Responsibility Principle**，Router 應僅負責 HTTP 請求處理。

## Current State

### Router 層（不良實作）
```python
# app/routers/financial.py L175-183
client = get_mops_client()
content = await client.download_xbrl(stock_id, year, q)
parser = get_xbrl_parser()
package = parser.parse(content, stock_id, year, q)
# ... 業務邏輯 ...
```

### Service 層（正確實作）
其他 endpoint（`get_balance_sheet`, `get_income_statement`, `get_cash_flow`）正確地委派給 `FinancialService`：
```python
service = get_financial_service()
statement = await service.get_financial_statement(...)
```

## Pain Points

1. **職責不清**: Router 包含業務邏輯，難以測試和維護
2. **重複風險**: 未來可能在其他地方複製類似邏輯
3. **架構不一致**: 同一個 Router 中有兩種風格
4. **快取遺漏**: `get_simplified_statement` 沒有使用資料庫快取

## Goals

1. 將 `get_simplified_statement` 的業務邏輯移至 `FinancialService`
2. 新增 `FinancialService.get_simplified_statement()` 方法
3. Router 僅保留 HTTP 處理邏輯
4. 維持 API 行為完全相容

## Constraints

- 不改變 API 回傳格式
- 不影響現有的其他 endpoint
- 保持後向相容
