from typing import Optional, List
from pydantic import BaseModel


class DividendRecord(BaseModel):
    """股利分派記錄"""
    stock_id: str                     # 股票代號
    company_name: str                 # 公司名稱
    year: int                         # 股利所屬年度 (民國年)
    quarter: Optional[int] = None     # 季度 (1-4, None=年度股利)
    period_start: Optional[str] = None  # 股利所屬期間起
    period_end: Optional[str] = None    # 股利所屬期間迄
    
    # 董事會決議
    board_resolution_date: Optional[str] = None  # 董事會決議日
    
    # 現金股利
    cash_dividend: Optional[float] = None  # 每股現金股利 (元)
    
    # 股票股利
    stock_dividend: Optional[float] = None  # 每股股票股利 (元)
    
    # 合計
    total_dividend: Optional[float] = None  # 合計股利
    
    # Ex-dividend information
    ex_dividend_date: Optional[str] = None  # 除息日
    ex_rights_date: Optional[str] = None     # 除權日


class DividendSummary(BaseModel):
    """股利彙總"""
    stock_id: str
    company_name: str
    year: int
    
    # 年度合計
    total_cash_dividend: float = 0.0
    total_stock_dividend: float = 0.0
    total_dividend: float = 0.0
    
    # 季度明細
    quarterly_dividends: List[DividendRecord] = []


class DividendResponse(BaseModel):
    """股利查詢回應"""
    stock_id: str
    company_name: str
    year_start: int
    year_end: int
    count: int
    records: List[DividendRecord]
