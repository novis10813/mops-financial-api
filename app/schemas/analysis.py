"""
Analysis Metrics Schemas
"""
from typing import List, Optional, Any
from decimal import Decimal
from pydantic import BaseModel, Field


class MetricDataPoint(BaseModel):
    """單一時間點的指標數據"""
    year: int
    quarter: int
    value: float
    unit: str = ""
    note: Optional[str] = None


class CompanyMetric(BaseModel):
    """公司的指標數據序列"""
    stock_id: str
    company_name: Optional[str] = None
    metric_name: str
    data: List[MetricDataPoint]


class ChartRequest(BaseModel):
    """圖表請求參數"""
    stock_ids: List[str] = Field(..., description="股票代號列表")
    metric: str = Field(..., description="指標名稱 (e.g., ROE)")
    years: int = Field(5, description="最近幾年")
