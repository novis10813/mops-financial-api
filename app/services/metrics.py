"""
Metrics Service
Calculates financial metrics like ROE, ROA, etc.
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

from app.schemas.analysis import CompanyMetric, MetricDataPoint
from app.services.financial import get_financial_service, FinancialService

logger = logging.getLogger(__name__)


class MetricsService:
    def __init__(self):
        self.financial_service = get_financial_service()

    async def get_roe_series(
        self, 
        stock_id: str, 
        start_year: int, 
        quarters: int
    ) -> CompanyMetric:
        """
        取得 ROE 數據序列
        
        Args:
            stock_id: 股票代號
            start_year: 開始年份 (e.g. 109)
            quarters: 總共要抓幾季
            
        Returns:
            CompanyMetric with list of data points
        """
        # 生成要查詢的 時間點 (year, quarter)
        # 倒序生成，從最近的開始
        targets = []
        current_year = 113  # TODO: 動態取得當前年份
        current_q = 3       # TODO: 動態取得當前季度
        
        # 簡單起見，我們先做最近 N 年的 Q4 (年報) 比較，或者是最近 N 季
        # 用戶指令: !plot 2330 2887 ROE 5 (年)
        # 根據之前的討論，我們顯示"季度"變化圖會比較細緻。
        
        # 產生最近 quarters 個季度的列表
        # 假設從 113 Q3 往回推
        y, q = current_year, current_q
        for _ in range(quarters):
            targets.append((y, q))
            q -= 1
            if q < 1:
                q = 4
                y -= 1
        
        targets.reverse() # 轉為時間順序
        
        logger.info(f"Calculating ROE for {stock_id} over {len(targets)} periods")
        
        # 並行抓取資料
        tasks = []
        for y, q in targets:
            tasks.append(self._calculate_single_roe(stock_id, y, q))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data_points = []
        for (y, q), result in zip(targets, results):
            if isinstance(result, Exception):
                logger.error(f"Error calc ROE for {stock_id} {y}Q{q}: {result}")
                continue
            
            if result is not None:
                data_points.append(MetricDataPoint(
                    year=y,
                    quarter=q,
                    value=float(result),
                    unit="%"
                ))
                
        return CompanyMetric(
            stock_id=stock_id,
            metric_name="ROE",
            data=data_points
        )

    async def _calculate_single_roe(self, stock_id: str, year: int, quarter: int) -> Optional[Decimal]:
        """計算單一季度的 ROE"""
        try:
            # 1. 取得損益表 (自動計算 Q4 單季)
            income_stmt = await self.financial_service.get_financial_statement(
                stock_id, year, quarter, "income_statement", format="flat"
            )
            
            # 2. 取得資產負債表
            bs_stmt = await self.financial_service.get_financial_statement(
                stock_id, year, quarter, "balance_sheet", format="flat"
            )
            
            # 3. 提取數值
            net_income = self._find_value(income_stmt.items, [
                "ProfitLossAttributableToOwnersOfParent",
                "ProfitLoss", 
                "本期淨利歸屬於母公司業主",
                "本期淨利"
            ])
            
            equity = self._find_value(bs_stmt.items, [
                "EquityAttributableToOwnersOfParent",
                "Equity",
                "歸屬於母公司業主之權益",
                "權益總計"
            ])
            
            if net_income is not None and equity is not None and equity != 0:
                # ROE = 淨利 / 權益 * 100
                roe = (net_income / equity) * 100
                return round(roe, 2)
                
            return None

        except Exception as e:
            logger.error(f"Failed to calculate ROE: {e}")
            return None

    def _find_value(self, items: List, keys: List[str]) -> Optional[Decimal]:
        """從扁平列表中依照優先順序查找數值"""
        # 建立快速查找 map
        lookup = {item.account_code: item.value for item in items if item.value is not None}
        name_lookup = {item.account_name: item.value for item in items if item.value is not None}
        
        for key in keys:
            # 嘗試代碼
            if key in lookup:
                return lookup[key]
            # 嘗試名稱
            if key in name_lookup:
                return name_lookup[key]
            
            # 模糊搜尋代碼 (e.g. "ProfitLoss" matching "ProfitLossFrom...")
            # 只有當 key 是英文時才做模糊搜尋，避免中文誤判
            if key.isascii():
                for code, val in lookup.items():
                    if key in code:
                        return val
                        
        return None


# Singleton
_metrics_service: Optional[MetricsService] = None

def get_metrics_service() -> MetricsService:
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
