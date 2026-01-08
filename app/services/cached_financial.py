"""
Cached Financial Service

Extends FinancialService with database caching support.
Checks database first before fetching from MOPS.
"""
import logging
from typing import Optional

from app.services.financial import FinancialService, FinancialServiceError
from app.schemas.financial import FinancialStatement
from app.db import get_session, FinancialRepository


logger = logging.getLogger(__name__)


class CachedFinancialService(FinancialService):
    """
    財務報表服務（帶快取）
    
    使用策略：
    1. 先查詢資料庫
    2. 若存在則直接返回（快取命中）
    3. 若不存在則從 MOPS 下載、儲存後返回
    """
    
    async def get_financial_statement(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        report_type: str = "balance_sheet",
        format: str = "tree",
        use_cache: bool = True,
        refresh: bool = False,
    ) -> FinancialStatement:
        """
        取得財務報表（支援快取）
        
        Args:
            stock_id: 股票代號
            year: 民國年
            quarter: 季度 (1-4)
            report_type: 報表類型
            format: 輸出格式
            use_cache: 是否使用快取（預設 True）
            refresh: 是否強制刷新快取（預設 False）
        """
        download_quarter = quarter if quarter else 4
        
        # 1. 嘗試從快取取得 (除非 refresh=True)
        if use_cache and not refresh:
            try:
                cached = await self._get_from_cache(
                    stock_id, year, download_quarter, report_type
                )
                if cached:
                    logger.info(f"Cache HIT: {stock_id} {year}Q{download_quarter} {report_type}")
                    # 處理格式轉換
                    if format == "flat":
                        cached.items = self._flatten_items(cached.items)
                    return cached
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # 2. 快取未命中，從 MOPS 取得
        logger.info(f"Cache MISS: {stock_id} {year}Q{download_quarter} {report_type}")
        statement = await super().get_financial_statement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_type=report_type,
            format="tree",  # 先用 tree 格式儲存
        )
        
        # 3. 儲存到快取
        if use_cache:
            try:
                await self._save_to_cache(statement)
                logger.info(f"Cached: {stock_id} {year}Q{download_quarter} {report_type}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        # 4. 格式轉換後返回
        if format == "flat":
            statement.items = self._flatten_items(statement.items)
        
        return statement
    
    async def _get_from_cache(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
    ) -> Optional[FinancialStatement]:
        """從資料庫快取取得報表"""
        async with get_session() as session:
            repo = FinancialRepository(session)
            return await repo.get_report(stock_id, year, quarter, report_type)
    
    async def _save_to_cache(self, statement: FinancialStatement) -> None:
        """儲存報表到資料庫快取"""
        async with get_session() as session:
            repo = FinancialRepository(session)
            await repo.save_report(statement)


# Singleton instance
_cached_service: Optional[CachedFinancialService] = None


def get_cached_financial_service() -> CachedFinancialService:
    """Get cached financial service instance (singleton)"""
    global _cached_service
    if _cached_service is None:
        _cached_service = CachedFinancialService()
    return _cached_service
