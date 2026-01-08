"""
Numeric parsing utilities for financial data

Provides consistent handling of financial value strings:
- Comma separators (e.g., "1,234,567")
- Whitespace trimming
- Empty/dash values
- Negative numbers and decimals
"""
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
    
    # 空值檢查 (包含半形和全形破折號)
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
    
    用於快速判斷，不執行完整解析。
    支援負數和小數。
    
    Args:
        value_str: 要檢查的字串
        
    Returns:
        True 如果是有效數值字串，否則 False
        
    Examples:
        >>> is_numeric_string("1234")
        True
        >>> is_numeric_string("-1,234.56")
        True
        >>> is_numeric_string("abc")
        False
    """
    if value_str is None:
        return False
    
    cleaned = str(value_str).replace(",", "").strip()
    if not cleaned or cleaned in ("-", "—"):
        return False
    
    # 支援負數和小數：移除負號，僅允許一個小數點
    test_str = cleaned.lstrip('-')
    if test_str.count('.') > 1:
        return False
    
    return test_str.replace('.', '', 1).isdigit()
