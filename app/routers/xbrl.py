"""
XBRL API Router
Provides endpoints for raw XBRL data access
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.schemas.xbrl import XBRLPackage, XBRLDownloadResponse
from app.services.mops_xbrl_client import get_mops_client, MOPSClientError
from app.services.xbrl_parser import get_xbrl_parser, XBRLParserError

router = APIRouter()


@router.get(
    "/{stock_id}/download",
    response_class=Response,
    summary="下載原始 XBRL ZIP",
    description="下載指定公司的原始 XBRL ZIP 檔案"
)
async def download_xbrl(
    stock_id: str,
    year: int = Query(..., description="民國年"),
    quarter: int = Query(..., ge=1, le=4, description="季度 1-4"),
):
    """
    下載原始 XBRL ZIP 檔案
    
    直接從 MOPS 下載並回傳 ZIP 檔案
    """
    client = get_mops_client()
    
    try:
        zip_content = await client.download_xbrl(stock_id, year, quarter)
        
        filename = f"{stock_id}_{year}Q{quarter}_xbrl.zip"
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except MOPSClientError as e:
        raise HTTPException(status_code=500, detail=str(e.message))


@router.get(
    "/{stock_id}/parsed",
    response_model=XBRLPackage,
    summary="取得解析後的 XBRL 資料",
    description="下載並解析 XBRL，回傳結構化資料"
)
async def get_parsed_xbrl(
    stock_id: str,
    year: int = Query(..., description="民國年"),
    quarter: int = Query(..., ge=1, le=4, description="季度 1-4"),
):
    """
    取得解析後的 XBRL Package
    
    包含：
    - calculation_arcs: 計算連結庫（包含 weight 加減邏輯）
    - presentation_arcs: 展示連結庫（階層結構）
    - facts: 數值資料
    - labels: 中英文標籤
    """
    client = get_mops_client()
    parser = get_xbrl_parser()
    
    try:
        content = await client.download_xbrl(stock_id, year, quarter)
        package = parser.parse(content, stock_id, year, quarter)
        return package
    except MOPSClientError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except XBRLParserError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{stock_id}/calculation-arcs",
    summary="取得 Calculation Linkbase",
    description="取得運算邏輯定義（weight 屬性指示加減）"
)
async def get_calculation_arcs(
    stock_id: str,
    year: int = Query(..., description="民國年"),
    quarter: int = Query(..., ge=1, le=4, description="季度 1-4"),
):
    """
    取得 Calculation Linkbase
    
    這是判斷「哪些項目相加、哪些項目相減」的核心資料：
    - weight = 1.0: 該項目加到父節點
    - weight = -1.0: 該項目從父節點減去
    
    例如：營業毛利 = 營業收入(+1.0) + 營業成本(-1.0)
    """
    client = get_mops_client()
    parser = get_xbrl_parser()
    
    try:
        content = await client.download_xbrl(stock_id, year, quarter)
        package = parser.parse(content, stock_id, year, quarter)
        
        return {
            "stock_id": stock_id,
            "year": year,
            "quarter": quarter,
            "calculation_arcs": package.calculation_arcs,
            "total_parents": len(package.calculation_arcs),
            "total_arcs": sum(len(v) for v in package.calculation_arcs.values()),
        }
    except MOPSClientError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except XBRLParserError as e:
        raise HTTPException(status_code=500, detail=str(e))
