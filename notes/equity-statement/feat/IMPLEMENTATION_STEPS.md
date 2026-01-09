# 實作步驟

## 檢查點

| Step | 狀態 | 說明 |
|------|:----:|------|
| 1 | ⬜ | 修改 Service Layer |
| 2 | ⬜ | 新增 Router Endpoint |
| 3 | ⬜ | 執行測試 |
| 4 | ⬜ | 手動驗證 |

---

## Step 1: 修改 Service Layer

### 任務
修改 `app/services/financial.py`：

1. 在 `REPORT_ROLES` (line 40-44) 新增：
```python
"equity_statement": "StatementOfChangesInEquity",
```

2. 在 `CUMULATIVE_REPORTS` (line 47) 新增：
```python
CUMULATIVE_REPORTS = {"income_statement", "equity_statement"}
```

### 驗證
```bash
uv run python -c "from app.services.financial import FinancialService; print(FinancialService.REPORT_ROLES)"
```

---

## Step 2: 新增 Router Endpoint

### 任務
修改 `app/routers/financial.py`：

1. 在 `get_cash_flow` 之後新增 `get_equity_statement` endpoint
2. 更新 `get_simplified_statement` 中的 `valid_types` 列表

### 測試
```python
# 確認 endpoint 存在
from app.routers.financial import router
assert any("/equity-statement" in str(r.path) for r in router.routes)
```

### 驗證
```bash
uv run uvicorn app.main:app --reload --port 8000 &
curl -s "http://localhost:8000/openapi.json" | grep equity-statement
```

---

## Step 3: 執行測試

### 驗證
```bash
uv run pytest tests/ -v
```

預期結果：所有測試通過

---

## Step 4: 手動驗證

### 驗證
```bash
# 基本查詢
curl "http://localhost:8000/financial/2330/equity-statement?year=113&quarter=3"

# Q4 單季
curl "http://localhost:8000/financial/2330/equity-statement?year=113&quarter=4"

# FinMind 格式
curl "http://localhost:8000/financial/2330/simplified/equity_statement?year=113&quarter=3"
```

預期結果：
- 回傳 200 OK
- `report_type: "equity_statement"`
- Q4 回傳 `is_standalone: true`
