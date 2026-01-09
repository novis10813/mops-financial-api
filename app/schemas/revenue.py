from typing import Optional, List
from pydantic import BaseModel


class MonthlyRevenue(BaseModel):
    """月營收資料模型"""
    stock_id: str               # 股票代號
    company_name: str           # 公司名稱
    year: int                   # 民國年
    month: int                  # 月份
    revenue: Optional[int] = None          # 本月營收 (千元)
    revenue_last_month: Optional[int] = None  # 上月營收
    revenue_last_year: Optional[int] = None   # 去年當月營收
    mom_change: Optional[float] = None        # 上月比較增減率 (%)
    yoy_change: Optional[float] = None        # 去年同月增減率 (%)
    accumulated_revenue: Optional[int] = None # 當月累計營收
    accumulated_last_year: Optional[int] = None  # 去年累計營收
    accumulated_yoy_change: Optional[float] = None  # 前期比較增減率 (%)
    comment: Optional[str] = None             # 備註


class MarketRevenueResponse(BaseModel):
    """全市場月營收回應"""
    year: int
    month: int
    market: str
    count: int
    data: List[MonthlyRevenue]
