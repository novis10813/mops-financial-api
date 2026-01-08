# Implementation Steps: Numeric Utils Refactoring

## Checklist

### Phase 1: Create Utils Module
- [ ] 建立 `app/utils/__init__.py`
- [ ] 建立 `app/utils/numerics.py`
- [ ] 建立 `tests/test_numerics.py` 並通過測試

### Phase 2: Migrate Services
- [ ] 更新 `app/services/xbrl_parser.py` L196
- [ ] 更新 `app/services/financial.py` L175-176 (Q4 計算)
- [ ] 更新 `app/services/financial.py` L298 (fallback items)
- [ ] 更新 `app/services/financial.py` L353 (tree builder)

### Phase 3: Migrate Router
- [ ] 更新 `app/routers/financial.py` L206

### Phase 4: Verification
- [ ] 執行 `uv run pytest tests/ -v`
- [ ] 確認所有測試通過

---

## Step-by-Step Details

### Step 1: Create `app/utils/__init__.py`

```python
"""Utility modules for mops-financial-api"""
from app.utils.numerics import parse_financial_value, is_numeric_string

__all__ = ["parse_financial_value", "is_numeric_string"]
```

### Step 2: Create `app/utils/numerics.py`

實作 `parse_financial_value()` 和 `is_numeric_string()` 函式。
（詳見 DESIGN_v1.md）

### Step 3: Create `tests/test_numerics.py`

```python
import pytest
from decimal import Decimal
from app.utils.numerics import parse_financial_value, is_numeric_string

class TestParseFinancialValue:
    def test_simple_integer(self):
        assert parse_financial_value("1234") == Decimal("1234")
    
    def test_with_commas(self):
        assert parse_financial_value("1,234,567") == Decimal("1234567")
    
    def test_negative(self):
        assert parse_financial_value("-1234") == Decimal("-1234")
    
    def test_decimal(self):
        assert parse_financial_value("123.45") == Decimal("123.45")
    
    def test_negative_with_commas(self):
        assert parse_financial_value("-1,234.56") == Decimal("-1234.56")
    
    def test_none(self):
        assert parse_financial_value(None) is None
    
    def test_empty_string(self):
        assert parse_financial_value("") is None
    
    def test_dash(self):
        assert parse_financial_value("-") is None
    
    def test_full_width_dash(self):
        assert parse_financial_value("—") is None
    
    def test_whitespace(self):
        assert parse_financial_value("  1234  ") == Decimal("1234")
    
    def test_invalid_string(self):
        assert parse_financial_value("abc") is None


class TestIsNumericString:
    def test_valid(self):
        assert is_numeric_string("1234") is True
    
    def test_invalid(self):
        assert is_numeric_string("abc") is False
```

### Step 4-7: Update Files

各檔案替換示例：

**xbrl_parser.py L196**:
```diff
- raw_value = raw_value.replace(",", "")
+ from app.utils.numerics import parse_financial_value
+ # 在建立 XBRLFact 時使用 parse_financial_value
```

**financial.py L175-176**:
```diff
- q4_clean = str(q4_value).replace(",", "").strip() if q4_value else ""
- q3_clean = str(q3_value).replace(",", "").strip() if q3_value else ""
+ q4_num = parse_financial_value(q4_value)
+ q3_num = parse_financial_value(q3_value)
```

### Step 8: Run Tests

```bash
uv run pytest tests/ -v
```

預期：所有測試通過，包含新增的 `test_numerics.py`。
