"""
Insiders Router - 董監事持股與質押 API

Insider & Ownership domain endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.services.insiders import (
    get_insiders_service,
    PledgingResponse,
    InsidersServiceError,
)

router = APIRouter(prefix="/insiders", tags=["Insiders - 籌碼與治理面"])


@router.get(
    "/pledge/{stock_id}",
    response_model=PledgingResponse,
    summary="取得董監事質押",
    description="取得指定公司的董監事持股與質押資料。質押比例過高可能代表大股東資金壓力。"
)
async def get_share_pledging(
    stock_id: str,
    year: int = Query(..., ge=102, le=200, description="民國年 (e.g., 113)"),
    month: int = Query(..., ge=1, le=12, description="月份 (1-12)"),
    market: str = Query(
        "sii",
        pattern="^(sii|otc)$",
        description="市場類型: sii=上市, otc=上櫃"
    ),
):
    """
    取得董監事質押資料
    
    ## 使用場景
    - **風險監控**: 質押比例過高可能代表大股東資金壓力
    - **公司治理評估**: 了解內部人持股與質押情況
    - **斷頭風險觀察**: 高質押比例在股價下跌時有斷頭風險
    
    ## 回傳資料
    - **summary**: 彙總資料（全體董監持股、設質股數、設質比例）
    - **details**: 個別董監事的持股與質押明細
    
    ## 重要欄位
    - `pledge_ratio`: 設質比例 (%)，超過 50% 需特別注意
    - `current_shares`: 目前持股數
    - `pledged_shares`: 設質股數
    """
    service = get_insiders_service()
    
    try:
        result = await service.get_share_pledging(stock_id, year, month, market)
        return result
    
    except InsidersServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/pledge",
    summary="取得董監事質押 (Query)",
    description="取得指定公司的董監事質押資料（使用 Query 參數）。"
)
async def get_share_pledging_query(
    stock_id: str = Query(..., description="股票代號"),
    year: int = Query(..., ge=102, le=200, description="民國年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    market: str = Query("sii", pattern="^(sii|otc)$"),
):
    """
    取得董監事質押資料 (Query 參數版)
    """
    service = get_insiders_service()
    
    try:
        result = await service.get_share_pledging(stock_id, year, month, market)
        return result
    
    except InsidersServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
