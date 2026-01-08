# Design v1: Numeric Utils Module

## Proposed Architecture

新增 `app/utils/numerics.py` 模組，提供統一的數值解析函式。

```
app/
├── utils/
│   ├── __init__.py       # [NEW]
│   └── numerics.py       # [NEW] 數值解析工具
├── services/
│   ├── xbrl_parser.py    # [MODIFY] 使用 parse_financial_value
│   └── financial.py      # [MODIFY] 使用 parse_financial_value
└── routers/
    └── financial.py      # [MODIFY] 使用 parse_financial_value
```

## Core Function Design

```python
# app/utils/numerics.py

from decimal import Decimal, InvalidOperation
from typing import Optional

def parse_financial_value(value_str: Optional[str]) -> Optional[Decimal]:
    """
    解析財報數值字串為 Decimal
    
    處理：
    - 逗號分隔符 (e.g., "1,234,567")
    - 前後空白
    - 空值/破折號/空字串
    - 負數 (e.g., "-1234")
    - 小數 (e.g., "123.45")
    
    Args:
        value_str: 原始數值字串
        
    Returns:
        Decimal 值，若無法解析則返回 None
        
    Examples:
        >>> parse_financial_value("1,234,567")
        Decimal('1234567')
        >>> parse_financial_value("-1,234.56")
        Decimal('-1234.56')
        >>> parse_financial_value("")
        None
        >>> parse_financial_value("-")
        None
    """
    if value_str is None:
        return None
    
    # 清理字串
    cleaned = str(value_str).replace(",", "").strip()
    
    # 空值檢查
    if not cleaned or cleaned in ("-", "—", ""):
        return None
    
    # 嘗試轉換
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def is_numeric_string(value_str: Optional[str]) -> bool:
    """
    檢查字串是否為有效的數值
    
    用於快速判斷，不執行完整解析
    """
    if value_str is None:
        return False
    
    cleaned = str(value_str).replace(",", "").strip()
    if not cleaned or cleaned in ("-", "—"):
        return False
    
    # 支援負數和小數
    return cleaned.lstrip('-').replace('.', '', 1).isdigit()
```

## Pros and Cons

### Pros
- ✅ 消除重複代碼 (DRY)
- ✅ 統一邊界條件處理
- ✅ 可獨立單元測試
- ✅ 未來改進只需修改一處

### Cons
- ⚠️ 新增一層函式呼叫（效能影響可忽略）
- ⚠️ 需要更新所有呼叫點

## Migration Strategy

1. **Phase 1**: 新增 `app/utils/numerics.py` 並加入測試
2. **Phase 2**: 逐一替換各檔案中的重複邏輯
3. **Phase 3**: 執行現有測試確保無回歸

## Decision

✅ **採用此設計** - 這是標準的 Extract Function 重構模式，風險低且效益明確。
