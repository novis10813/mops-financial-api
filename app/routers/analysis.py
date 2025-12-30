"""
Analysis Router
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import List

from app.services.metrics import get_metrics_service
from app.services.chart import get_chart_service

router = APIRouter()

@router.get(
    "/chart/compare",
    summary="Generate Comparison Chart",
    description="Generates a PNG chart comparing metrics for multiple stocks",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}}
        }
    }
)
async def get_comparison_chart(
    stocks: str = Query(..., description="Comma separated stock IDs (e.g. '2330,2887')"),
    metric: str = Query("ROE", description="Metric to plot (Currently only support ROE)"),
    years: int = Query(5, description="Number of years (or quarters) to look back"),
):
    metric_service = get_metrics_service()
    chart_service = get_chart_service()
    
    stock_list = [s.strip() for s in stocks.split(",")]
    metrics_data = []
    
    # 目前先根據 years 轉換成 quarters 數量 (簡單起見 1 year = 4 quarters)
    # 使用者輸入 5 代表 5 年 = 20 季
    quarters_count = years * 4
    
    for stock_id in stock_list:
        if metric.upper() == "ROE":
            data = await metric_service.get_roe_series(stock_id, 109, quarters_count)
            metrics_data.append(data)
        else:
             raise HTTPException(status_code=400, detail=f"Metric {metric} not supported yet")
    
    if not metrics_data:
        raise HTTPException(status_code=404, detail="No data found")
        
    # Generate Chart
    img_bytes = chart_service.generate_comparison_chart(
        metrics_data,
        title=f"{metric} Comparison: {', '.join(stock_list)}"
    )
    
    return Response(content=img_bytes, media_type="image/png")
