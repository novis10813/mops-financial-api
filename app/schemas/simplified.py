"""
Simplified Financial Statement Schema

Provides a standardized, simplified format similar to FinMind/FinLab
Only includes major line items without detailed breakdowns
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class SimplifiedFinancialItem(BaseModel):
    """A single financial line item in simplified format"""
    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    stock_id: str = Field(..., description="Stock ID")
    type: str = Field(..., description="Financial metric type (e.g., 'Revenue', 'GrossProfit')")
    value: Optional[float] = Field(None, description="Numeric value")
    origin_name: str = Field(..., description="Original Chinese name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-09-30",
                "stock_id": "2330",
                "type": "Revenue",
                "value": 759690482000,
                "origin_name": "營業收入"
            }
        }


class SimplifiedFinancialStatement(BaseModel):
    """Simplified financial statement response"""
    stock_id: str
    year: int  # 民國年
    quarter: int
    report_date: str  # YYYY-MM-DD
    statement_type: str  # "income_statement", "balance_sheet", "cash_flow"
    items: List[SimplifiedFinancialItem]
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_id": "2330",
                "year": 113,
                "quarter": 3,
                "report_date": "2024-09-30",
                "statement_type": "income_statement",
                "items": [
                    {
                        "date": "2024-09-30",
                        "stock_id": "2330",
                        "type": "Revenue",
                        "value": 759690482000,
                        "origin_name": "營業收入"
                    }
                ]
            }
        }


# Standard mapping for major financial statement items
# Maps XBRL concept names to simplified type names

INCOME_STATEMENT_MAPPING = {
    # Revenue & Cost
    "Revenue": "Revenue",  # 營業收入
    "OperatingRevenue": "Revenue",
    "CostOfGoodsSold": "CostOfGoodsSold",  # 營業成本
    "CostOfSales": "CostOfGoodsSold",
    "GrossProfit": "GrossProfit",  # 營業毛利
    "GrossProfitLoss": "GrossProfit",
    "GrossProfitLossFromOperations": "GrossProfit",
    
    # Operating Expenses
    "OperatingExpenses": "OperatingExpenses",  # 營業費用
    "SellingExpenses": "SellingExpenses",  # 推銷費用
    "AdministrativeExpenses": "AdministrativeExpenses",  # 管理費用
    "ResearchAndDevelopmentExpense": "ResearchAndDevelopmentExpense",  # 研發費用
    
    # Operating Income
    "OperatingIncome": "OperatingIncome",  # 營業利益
    "OperatingIncomeLoss": "OperatingIncome",
    "ProfitLossFromOperatingActivities": "OperatingIncome",
    
    # Non-Operating
    "NonoperatingIncomeAndExpenses": "NonOperatingIncome",  # 營業外收支
    "OtherIncome": "OtherIncome",  # 其他收入
    "OtherGainsAndLosses": "OtherGainsAndLosses",  # 其他利益及損失
    "FinanceCosts": "FinanceCosts",  # 財務成本
    "InterestExpense": "InterestExpense",  # 利息費用
    
    # Pre-tax & Tax
    "ProfitLossBeforeTax": "ProfitBeforeTax",  # 稅前淨利
    "IncomeTaxExpense": "IncomeTaxExpense",  # 所得稅費用
    
    # Net Income
    "ProfitLoss": "NetIncome",  # 本期淨利
    "ProfitLossAttributableToOwnersOfParent": "NetIncomeAttributableToOwners",  # 母公司淨利
    
    # EPS
    "BasicEarningsPerShare": "EPS",  # 基本每股盈餘
}

BALANCE_SHEET_MAPPING = {
    # Assets
    "Assets": "TotalAssets",  # 資產總計
    "CurrentAssets": "CurrentAssets",  # 流動資產
    "NoncurrentAssets": "NoncurrentAssets",  # 非流動資產
    "CashAndCashEquivalents": "Cash",  # 現金及約當現金
    "AccountsReceivable": "AccountsReceivable",  # 應收帳款
    "AccountsReceivableNet": "AccountsReceivable",
    "Inventories": "Inventory",  # 存貨
    "PropertyPlantAndEquipment": "PPE",  # 不動產、廠房及設備
    "IntangibleAssets": "IntangibleAssets",  # 無形資產
    
    # Liabilities
    "Liabilities": "TotalLiabilities",  # 負債總計
    "CurrentLiabilities": "CurrentLiabilities",  # 流動負債
    "NoncurrentLiabilities": "NoncurrentLiabilities",  # 非流動負債
    "ShortTermBorrowings": "ShortTermDebt",  # 短期借款
    "LongTermBorrowings": "LongTermDebt",  # 長期借款
    "AccountsPayable": "AccountsPayable",  # 應付帳款
    
    # Equity
    "Equity": "TotalEquity",  # 權益總計
    "EquityAttributableToOwnersOfParent": "EquityAttributableToOwners",  # 母公司權益
    "Share": "ShareCapital",  # 股本
    "CapitalSurplus": "CapitalSurplus",  # 資本公積
    "RetainedEarnings": "RetainedEarnings",  # 保留盈餘
}

CASH_FLOW_MAPPING = {
    # Operating Activities
    "CashFlowsFromUsedInOperatingActivities": "OperatingCashFlow",  # 營業活動現金流量
    "ProfitLossBeforeTax": "ProfitBeforeTax",
    
    # Investing Activities
    "CashFlowsFromUsedInInvestingActivities": "InvestingCashFlow",  # 投資活動現金流量
    "PaymentsToAcquirePropertyPlantAndEquipment": "CapitalExpenditure",  # 資本支出
    
    # Financing Activities
    "CashFlowsFromUsedInFinancingActivities": "FinancingCashFlow",  # 籌資活動現金流量
    "DividendsPaid": "DividendsPaid",  # 支付股利
    
    # Net Change
    "IncreaseDecreaseInCashAndCashEquivalents": "NetCashChange",  # 現金淨增減
}


def get_statement_mapping(statement_type: str) -> dict:
    """Get the concept mapping for a statement type"""
    if statement_type == "income_statement":
        return INCOME_STATEMENT_MAPPING
    elif statement_type == "balance_sheet":
        return BALANCE_SHEET_MAPPING
    elif statement_type == "cash_flow":
        return CASH_FLOW_MAPPING
    else:
        return {}
