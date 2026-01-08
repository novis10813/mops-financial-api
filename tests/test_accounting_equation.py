"""
Tests for Accounting Equation Validation

The Fundamental Accounting Equation:
    Assets = Liabilities + Equity

This test validates that the financial data fetched from MOPS
adheres to this fundamental accounting identity.
"""
import pytest
from decimal import Decimal
from typing import Optional

from app.services.financial import get_financial_service, FinancialServiceError
from app.schemas.financial import FinancialStatement, FinancialItem


def find_item_by_concept(items: list[FinancialItem], concept: str) -> Optional[FinancialItem]:
    """
    遞迴搜尋財務報表項目中的特定 concept
    
    Args:
        items: 財務報表項目列表
        concept: XBRL concept 名稱 (e.g., 'Assets', 'Liabilities', 'Equity')
    
    Returns:
        找到的 FinancialItem，若未找到則返回 None
    """
    for item in items:
        if item.account_code == concept:
            return item
        if item.children:
            found = find_item_by_concept(item.children, concept)
            if found:
                return found
    return None


def extract_accounting_items(
    statement: FinancialStatement
) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """
    從資產負債表中提取會計恆等式所需的三個主要項目
    
    Returns:
        (assets, liabilities, equity) - 資產總計、負債總計、權益總計
    """
    assets_item = find_item_by_concept(statement.items, "Assets")
    liabilities_item = find_item_by_concept(statement.items, "Liabilities")
    equity_item = find_item_by_concept(statement.items, "Equity")
    
    assets = assets_item.value if assets_item else None
    liabilities = liabilities_item.value if liabilities_item else None
    equity = equity_item.value if equity_item else None
    
    return assets, liabilities, equity


@pytest.mark.asyncio
async def test_accounting_equation_tsmc_2024q3():
    """
    驗證台積電 (2330) 113年Q3 資產負債表的會計恆等式
    
    會計恆等式: Assets = Liabilities + Equity
    """
    service = get_financial_service()
    
    statement = await service.get_financial_statement(
        stock_id="2330",
        year=113,
        quarter=3,
        report_type="balance_sheet",
        format="tree",
    )
    
    assets, liabilities, equity = extract_accounting_items(statement)
    
    # 確保三個值都存在
    assert assets is not None, "Assets (資產總計) not found in balance sheet"
    assert liabilities is not None, "Liabilities (負債總計) not found in balance sheet"
    assert equity is not None, "Equity (權益總計) not found in balance sheet"
    
    # 驗證會計恆等式
    calculated = liabilities + equity
    
    assert assets == calculated, (
        f"Accounting equation violated!\n"
        f"  Assets:      {assets:>20,}\n"
        f"  Liabilities: {liabilities:>20,}\n"
        f"  Equity:      {equity:>20,}\n"
        f"  L + E:       {calculated:>20,}\n"
        f"  Difference:  {assets - calculated:>20,}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("stock_id,year,quarter", [
    ("2330", 113, 3),  # 台積電 TSMC
    ("2317", 113, 3),  # 鴻海 Foxconn
    ("2454", 113, 3),  # 聯發科 MediaTek
    ("2412", 113, 3),  # 中華電信 Chunghwa Telecom
    ("1301", 113, 3),  # 台塑 Formosa Plastics
])
async def test_accounting_equation_multiple_companies(stock_id: str, year: int, quarter: int):
    """
    驗證多家公司資產負債表的會計恆等式
    
    測試對象：台灣主要上市公司
    """
    service = get_financial_service()
    
    try:
        statement = await service.get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type="balance_sheet",
            format="tree",
        )
    except FinancialServiceError as e:
        pytest.skip(f"Failed to fetch data for {stock_id}: {e}")
    
    assets, liabilities, equity = extract_accounting_items(statement)
    
    # 確保三個值都存在
    assert assets is not None, f"{stock_id}: Assets not found"
    assert liabilities is not None, f"{stock_id}: Liabilities not found"
    assert equity is not None, f"{stock_id}: Equity not found"
    
    # 驗證會計恆等式
    calculated = liabilities + equity
    
    assert assets == calculated, (
        f"{stock_id} Accounting equation violated!\n"
        f"  Assets:      {assets:>20,}\n"
        f"  Liabilities: {liabilities:>20,}\n"
        f"  Equity:      {equity:>20,}\n"
        f"  L + E:       {calculated:>20,}\n"
        f"  Difference:  {assets - calculated:>20,}"
    )


@pytest.mark.asyncio
async def test_accounting_equation_annual_report():
    """
    驗證年報 (Q4/Annual) 的會計恆等式
    
    測試年報資料是否也符合會計恆等式
    """
    service = get_financial_service()
    
    # quarter=None 表示取得年報
    statement = await service.get_financial_statement(
        stock_id="2330",
        year=112,  # 112年年報
        quarter=None,
        report_type="balance_sheet",
        format="tree",
    )
    
    assets, liabilities, equity = extract_accounting_items(statement)
    
    assert assets is not None, "Assets not found in annual report"
    assert liabilities is not None, "Liabilities not found in annual report"
    assert equity is not None, "Equity not found in annual report"
    
    calculated = liabilities + equity
    
    assert assets == calculated, (
        f"Annual report accounting equation violated!\n"
        f"  Assets: {assets}, Liabilities: {liabilities}, Equity: {equity}\n"
        f"  Expected: {calculated}, Difference: {assets - calculated}"
    )
