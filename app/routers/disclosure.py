"""
Disclosure Router - 重大資訊揭露 API

Corporate Finance domain endpoints for disclosure data.
"""
from fastapi import APIRouter, Query, HTTPException

from app.services.disclosure import (
    get_disclosure_service,
    DisclosureServiceError,
)
from app.schemas.disclosure import DisclosureResponse

router = APIRouter(prefix="/disclosure", tags=["Corporate - 公司治理面"])


@router.get(
    "/{stock_id}",
    response_model=DisclosureResponse,
    summary="取得重大資訊揭露",
    description="取得公司的資金貸放與背書保證資訊。這些資訊揭示公司的財務風險敞口。"
)
async def get_disclosure(
    stock_id: str,
    year: int = Query(..., ge=100, le=200, description="民國年"),
    month: int = Query(..., ge=1, le=12, description="月份 (1-12)"),
    market: str = Query(
        "sii",
        pattern="^(sii|otc)$",
        description="市場類型: sii=上市, otc=上櫃"
    ),
):
    """
    取得重大資訊揭露資料
    
    ## 包含項目
    
    ### 1. 資金貸放 (Funds Lending)
    - 本公司/子公司資金貸放餘額
    - 本月/上月餘額比較
    - 最高限額
    
    ### 2. 背書保證 (Endorsement/Guarantee)
    - 本公司/子公司背書保證餘額
    - 本月增減金額
    - 最高額度
    
    ### 3. 本公司與子公司間背書保證
    - 本公司對子公司
    - 子公司對本公司
    
    ### 4. 對大陸地區背書保證
    - 本公司/子公司對大陸的背書保證
    
    ## 風險評估
    - 背書保證餘額過高可能有連帶債務風險
    - 需注意背書保證對象是否為關係人
    - 對大陸地區背書保證有政治風險考量
    """
    service = get_disclosure_service()
    
    try:
        result = await service.get_disclosure(stock_id, year, month, market)
        return result
    
    except DisclosureServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=DisclosureResponse,
    summary="取得重大資訊揭露 (Query)",
    description="使用 Query 參數取得資金貸放與背書保證資訊。"
)
async def get_disclosure_query(
    stock_id: str = Query(..., description="股票代號"),
    year: int = Query(..., ge=100, le=200, description="民國年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    market: str = Query("sii", pattern="^(sii|otc)$"),
):
    """Query 參數版本"""
    service = get_disclosure_service()
    
    try:
        result = await service.get_disclosure(stock_id, year, month, market)
        return result
    
    except DisclosureServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
