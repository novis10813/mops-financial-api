"""
Financial API Router
Provides endpoints for retrieving financial statements
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
    description="取得指定公司的資產負債表，包含完整階層結構與加減邏輯"
)
async def get_balance_sheet(
    stock_id: str,
    year: Optional[int] = Query(None, description="民國年（預設：最近一期）"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4（預設：最近一期）"),
    format: str = Query("tree", description="輸出格式: tree (階層) 或 flat (扁平)"),
):
    """
    取得資產負債表 (Statement of Financial Position)
    
    回傳的 FinancialItem 包含：
    - weight: 1.0 表示加項，-1.0 表示減項
    - level: 階層深度，可用於重建縮排
    - children: 子項目列表
    """
    # 若未指定年季，使用最近一期
    if year is None or quarter is None:
        # TODO: 實作自動偵測最新期別
        raise HTTPException(
            status_code=400, 
            detail="Year and quarter are required. Auto-detection not yet implemented."
        )
    
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
    description="取得指定公司的綜合損益表"
)
async def get_income_statement(
    stock_id: str,
    year: Optional[int] = Query(None, description="民國年"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4"),
    format: str = Query("tree", description="輸出格式: tree 或 flat"),
):
    """取得綜合損益表 (Statement of Comprehensive Income)"""
    if year is None or quarter is None:
        raise HTTPException(
            status_code=400,
            detail="Year and quarter are required."
        )
    
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
    year: Optional[int] = Query(None, description="民國年"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="季度 1-4"),
    format: str = Query("tree", description="輸出格式: tree 或 flat"),
):
    """取得現金流量表 (Statement of Cash Flows)"""
    if year is None or quarter is None:
        raise HTTPException(
            status_code=400,
            detail="Year and quarter are required."
        )
    
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
