"""
Financial API Router
Provides endpoints for retrieving financial statements

Parameter Logic:
- year + quarter: Get specific quarter data
- year only (no quarter): Get annual report (Q4 raw data)

Example:
- GET /2330/income-statement?year=113&quarter=4 → Q4 report
- GET /2330/income-statement?year=113 → Annual report (same as Q4)
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.financial import FinancialStatement
from app.services.financial import get_financial_service, FinancialServiceError

router = APIRouter()


@router.get(
    "/{stock_id}/balance-sheet",
    response_model=FinancialStatement,
    summary="取得資產負債表",
    description="取得指定公司的資產負債表（時點快照）"
)
async def get_balance_sheet(
    stock_id: str,
    year: int = Query(..., description="民國年（必填）"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4，不填則取年報"),
    format: str = Query("tree", description="輸出格式: tree (階層) 或 flat (扁平)"),
):
    """
    取得資產負債表 (Statement of Financial Position)
    
    - 資產負債表是「時點快照」，每季獨立，無累計問題
    - quarter=None: 取得年報（Q4 時點）
    - quarter=1~4: 取得該季末時點的資產負債表
    """
    service = get_financial_service()
    
    try:
        statement = await service.get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type="balance_sheet",
            format=format,
        )
        return statement
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{stock_id}/income-statement",
    response_model=FinancialStatement,
    summary="取得綜合損益表",
    description="取得指定公司的綜合損益表（累計型）"
)
async def get_income_statement(
    stock_id: str,
    year: int = Query(..., description="民國年（必填）"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4，不填則取年報"),
    format: str = Query("tree", description="輸出格式: tree 或 flat"),
):
    """
    取得綜合損益表 (Statement of Comprehensive Income)
    
    - 損益表是「累計型」報表
    - quarter=None: 取得年報原始資料（全年累計）
    - quarter=1~4: 取得該季報表（Q2, Q3, Q4 為累計）
    """
    service = get_financial_service()
    
    try:
        statement = await service.get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type="income_statement",
            format=format,
        )
        return statement
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{stock_id}/cash-flow",
    response_model=FinancialStatement,
    summary="取得現金流量表",
    description="取得指定公司的現金流量表"
)
async def get_cash_flow(
    stock_id: str,
    year: int = Query(..., description="民國年（必填）"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4，不填則取年報"),
    format: str = Query("tree", description="輸出格式: tree 或 flat"),
):
    """
    取得現金流量表 (Statement of Cash Flows)
    
    - 現金流量表為期間報表
    - quarter=None: 取得年報
    - quarter=1~4: 取得該季報表
    """
    service = get_financial_service()
    
    try:
        statement = await service.get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type="cash_flow",
            format=format,
        )
        return statement
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{stock_id}/equity-statement",
    response_model=FinancialStatement,
    summary="取得權益變動表",
    description="取得指定公司的權益變動表（累計型）"
)
async def get_equity_statement(
    stock_id: str,
    year: int = Query(..., description="民國年（必填）"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4，不填則取年報"),
    format: str = Query("tree", description="輸出格式: tree 或 flat"),
):
    """
    取得權益變動表 (Statement of Changes in Equity)
    
    - 權益變動表是「累計型」報表
    - quarter=None: 取得年報原始資料（全年累計）
    - quarter=1~4: 取得該季報表（累計）
    """
    service = get_financial_service()
    
    try:
        statement = await service.get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type="equity_statement",
            format=format,
        )
        return statement
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{stock_id}/simplified/{statement_type}",
    summary="取得 FinMind 格式財報",
    description="返回 FinMind 風格的扁平化財報格式"
)
async def get_simplified_statement(
    stock_id: str,
    statement_type: str,
    year: int = Query(..., description="民國年"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4，不填則取年報"),
):
    """
    取得 FinMind 風格的扁平化財報
    
    格式與 FinMind API 相同：
    ```json
    {
      "items": [
        {
          "date": "2024-09-30",
          "stock_id": "2330",
          "type": "CostOfGoodsSold",
          "value": 128352000000,
          "origin_name": "營業成本"
        }
      ]
    }
    ```
    
    返回所有財報科目，type 為 XBRL concept name
    """
    # 驗證 statement_type
    valid_types = ["income_statement", "balance_sheet", "cash_flow", "equity_statement"]
    if statement_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid statement_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # 委派給 Service 層
    service = get_financial_service()
    try:
        return await service.get_simplified_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            statement_type=statement_type,
        )
    except FinancialServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))



