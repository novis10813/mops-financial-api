"""
Financial data schemas
"""
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class FinancialItem(BaseModel):
    """單一財務科目項目"""
    account_code: str = Field(..., description="會計科目代碼 (e.g., '1100')")
    account_name: str = Field(..., description="科目名稱 (e.g., '現金及約當現金')")
    account_name_en: Optional[str] = Field(None, description="英文科目名稱")
    value: Optional[Decimal] = Field(None, description="數值")
    weight: float = Field(1.0, description="對父層的貢獻權重 (+1.0 加 / -1.0 減)")
    level: int = Field(0, description="階層深度 (0=頂層)")
    children: List["FinancialItem"] = Field(default_factory=list, description="子項目")
    
    class Config:
        json_schema_extra = {
            "example": {
                "account_code": "1100",
                "account_name": "現金及約當現金",
                "account_name_en": "Cash and cash equivalents",
                "value": "1234567890",
                "weight": 1.0,
                "level": 2,
                "children": []
            }
        }


class FinancialStatement(BaseModel):
    """完整財務報表"""
    stock_id: str = Field(..., description="股票代號")
    company_name: Optional[str] = Field(None, description="公司名稱")
    year: int = Field(..., description="民國年")
    quarter: Optional[int] = Field(None, ge=1, le=4, description="季度 (1-4)，None 表示年報")
    report_type: str = Field(..., description="報表類型: balance_sheet, income_statement, cash_flow")
    is_standalone: bool = Field(False, description="True 表示 Q4 單季資料（已扣除 Q3 累計）")
    items: List[FinancialItem] = Field(default_factory=list, description="財務項目")
    currency: str = Field("TWD", description="幣別")
    unit: str = Field("thousands", description="單位: thousands (千元) or units (元)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_id": "2330",
                "company_name": "台灣積體電路製造股份有限公司",
                "year": 113,
                "quarter": 3,
                "report_type": "balance_sheet",
                "items": [],
                "currency": "TWD",
                "unit": "thousands"
            }
        }


class FinancialQuery(BaseModel):
    """財務報表查詢參數"""
    year: Optional[int] = Field(None, description="民國年（預設：最近一期）")
    quarter: Optional[int] = Field(None, ge=1, le=4, description="季度 1-4（預設：最近一期）")
    format: str = Field("tree", description="輸出格式: tree (階層) 或 flat (扁平)")
