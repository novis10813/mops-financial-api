"""
Revenue Router - 月營收 API

Operations domain endpoints for monthly revenue data.
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException

from app.services.revenue import (
    get_revenue_service,
    MonthlyRevenue,
    MarketRevenueResponse,
    RevenueServiceError,
)

router = APIRouter(prefix="/revenue", tags=["Operations - 營運面"])


@router.get(
    "/monthly",
    response_model=MarketRevenueResponse,
    summary="取得月營收",
    description="取得指定月份的營收資料。可查詢全市場或單一公司。"
)
async def get_monthly_revenue(
    year: int = Query(..., ge=102, le=200, description="民國年 (e.g., 113)"),
    month: int = Query(..., ge=1, le=12, description="月份 (1-12)"),
    stock_id: Optional[str] = Query(None, description="股票代號，若不填則回傳全市場"),
    market: str = Query(
        "sii",
        pattern="^(sii|otc|rotc|pub)$",
        description="市場類型: sii=上市, otc=上櫃, rotc=興櫃, pub=公開發行"
    ),
):
    """
    取得月營收資料
    
    - **year**: 民國年 (102 以後，IFRS 採用後)
    - **month**: 月份 (1-12)
    - **stock_id**: 股票代號 (若不填則回傳全市場)
    - **market**: 市場類型
    
    回傳欄位說明：
    - revenue: 當月營收 (千元)
    - revenue_last_month: 上月營收
    - revenue_last_year: 去年同月營收
    - mom_change: 上月比較增減率 (%)
    - yoy_change: 去年同月增減率 (%)
    - accumulated_revenue: 當月累計營收
    - accumulated_last_year: 去年累計營收
    - accumulated_yoy_change: 前期比較增減率 (%)
    - comment: 備註 (說明營收變動原因)
    """
    service = get_revenue_service()
    
    try:
        if stock_id:
            # 查詢單一公司
            result = await service.get_single_revenue(stock_id, year, month, market)
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No revenue data found for {stock_id} in {year}/{month}"
                )
            return MarketRevenueResponse(
                year=year,
                month=month,
                market=market,
                count=1,
                data=[result],
            )
        else:
            # 查詢全市場
            data = await service.get_market_revenue(year, month, market)
            return MarketRevenueResponse(
                year=year,
                month=month,
                market=market,
                count=len(data),
                data=data,
            )
    
    except RevenueServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/monthly/{stock_id}",
    response_model=MonthlyRevenue,
    summary="取得單一公司月營收",
    description="取得指定公司的月營收資料。"
)
async def get_stock_monthly_revenue(
    stock_id: str,
    year: int = Query(..., ge=102, le=200, description="民國年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    market: str = Query(
        "sii",
        pattern="^(sii|otc|rotc|pub)$",
        description="市場類型"
    ),
):
    """
    取得單一公司月營收
    
    這是 /revenue/monthly?stock_id=xxx 的簡化版本。
    """
    service = get_revenue_service()
    
    try:
        result = await service.get_single_revenue(stock_id, year, month, market)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No revenue data found for {stock_id} in {year}/{month}"
            )
        return result
    
    except RevenueServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
