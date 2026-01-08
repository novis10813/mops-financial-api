"""
Financial API Router
Provides endpoints for retrieving financial statements

Parameter Logic:
- year + quarter: Get specific quarter data
- year only (no quarter): Get annual report (Q4 raw data)
- quarter=4: For income statement, calculates Q4 standalone = Annual - Q3

Example:
- GET /2330/income-statement?year=113&quarter=4 → Q4 single quarter
- GET /2330/income-statement?year=113 → Full year (annual report)
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
    description="取得指定公司的綜合損益表（累計型，Q4 會自動計算單季）"
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
    - quarter=1~3: 取得該季報表（Q2, Q3 為累計）
    - quarter=4: **自動計算 Q4 單季** = 年報 - Q3 累計
    
    注意：回傳的 is_standalone=True 表示已計算為單季資料
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
    from app.schemas.simplified import (
        SimplifiedFinancialStatement,
        SimplifiedFinancialItem,
    )
    from app.services.mops_client import get_mops_client, MOPSClientError
    from app.services.xbrl_parser import get_xbrl_parser
    from app.utils.numerics import parse_financial_value
    
    # Validate statement type
    valid_types = ["income_statement", "balance_sheet", "cash_flow"]
    if statement_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid statement_type. Must be one of: {', '.join(valid_types)}"
        )
    
    try:
        # Download XBRL directly
        client = get_mops_client()
        q = quarter or 4
        content = await client.download_xbrl(stock_id, year, q)
        
        # Parse XBRL
        parser = get_xbrl_parser()
        package = parser.parse(content, stock_id, year, q)
        
        # Calculate report date (西元年)
        western_year = year + 1911
        quarter_month = {1: "03", 2: "06", 3: "09", 4: "12"}
        quarter_day = {1: "31", 2: "30", 3: "30", 4: "31"}
        report_date = f"{western_year}-{quarter_month[q]}-{quarter_day[q]}"
        
        # Convert facts to FinMind format
        simplified_items = []
        seen_types = set()
        
        for fact in package.facts:
            concept = fact.concept
            if concept in seen_types:
                continue
            
            # Skip if no value
            if fact.value is None:
                continue
            
            # Convert value to float（使用統一工具）
            parsed = parse_financial_value(fact.value)
            if parsed is None:
                continue
            value_float = float(parsed)
            
            seen_types.add(concept)
            
            # Get Chinese label
            origin_name = package.labels.get(concept, concept)
            
            simplified_items.append(
                SimplifiedFinancialItem(
                    date=report_date,
                    stock_id=stock_id,
                    type=concept,
                    value=value_float,
                    origin_name=origin_name
                )
            )
        
        return SimplifiedFinancialStatement(
            stock_id=stock_id,
            year=year,
            quarter=q,
            report_date=report_date,
            statement_type=statement_type,
            items=simplified_items
        )
        
    except MOPSClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse XBRL: {str(e)}")



