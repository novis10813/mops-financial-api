"""
Dividend Router - 股利分派 API

Corporate Finance domain endpoints for dividend data.
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.services.dividend import (
    get_dividend_service,
    DividendServiceError,
)
from app.schemas.dividend import (
    DividendResponse,
    DividendSummary,
)

router = APIRouter(prefix="/dividend", tags=["Corporate - 公司治理面"])


@router.get(
    "/{stock_id}",
    response_model=DividendResponse,
    summary="取得股利分派",
    description="取得指定公司的股利分派資料。支援季配息公司（如台積電）。"
)
async def get_dividends(
    stock_id: str,
    year_start: int = Query(..., ge=100, le=200, description="起始年度 (民國年)"),
    year_end: Optional[int] = Query(None, ge=100, le=200, description="結束年度 (預設同起始年度)"),
    query_type: int = Query(
        2,
        ge=1, le=2,
        description="查詢類型: 1=董事會決議年度, 2=股利所屬年度"
    ),
):
    """
    取得股利分派資料
    
    ## 查詢類型說明
    - **1 (董事會決議年度)**: 以董事會決議日期為基準
    - **2 (股利所屬年度)**: 以股利所屬營業年度為基準（推薦）
    
    ## 回傳欄位
    - `year`: 股利所屬年度
    - `quarter`: 季度 (1-4, 年度股利為 null)
    - `cash_dividend`: 每股現金股利 (元)
    - `stock_dividend`: 每股股票股利 (元)
    - `board_resolution_date`: 董事會決議日
    
    ## 注意事項
    - 季配息公司（如台積電）會有 4 筆記錄
    - 年度配息公司只有 1 筆記錄
    """
    service = get_dividend_service()
    
    try:
        result = await service.get_dividends(
            stock_id, 
            year_start, 
            year_end,
            query_type,
        )
        return result
    
    except DividendServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{stock_id}/summary",
    response_model=DividendSummary,
    summary="取得年度股利彙總",
    description="取得指定公司的年度股利彙總，自動合計季度股利。"
)
async def get_annual_dividend_summary(
    stock_id: str,
    year: int = Query(..., ge=100, le=200, description="年度 (民國年)"),
):
    """
    取得年度股利彙總
    
    自動合計全年的現金股利和股票股利。
    
    ## 適用場景
    - 計算年度殖利率
    - 比較各年度股利變化
    - 季配息公司的年度合計
    """
    service = get_dividend_service()
    
    try:
        result = await service.get_annual_summary(stock_id, year)
        return result
    
    except DividendServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
