#!/usr/bin/env python
"""
測試 FinancialService 的 DB 快取功能（權益變動表）

使用方式:
  MOPS_POSTGRES_HOST=localhost MOPS_POSTGRES_PORT=5433 MOPS_POSTGRES_PASSWORD=devpassword \
    PYTHONPATH=. uv run python scripts/test_equity_caching.py
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    from app.db.connection import init_db, close_db, get_session
    from app.db.repository import FinancialRepository
    from app.services.financial import get_financial_service
    
    stock_id = "2330"  # 台積電
    year = 113
    quarter = 3
    report_type = "equity_statement"
    
    # 1. 初始化資料庫 (建立 tables)
    logger.info("=== Step 1: Initializing database ===")
    await init_db()
    logger.info("Database initialized successfully!")
    
    # 2. 檢查目前 DB 中是否有此報表
    logger.info(f"\n=== Step 2: Check if {stock_id} {year}Q{quarter} {report_type} exists in DB ===")
    async with get_session() as session:
        repo = FinancialRepository(session)
        exists = await repo.report_exists(stock_id, year, quarter, report_type)
        logger.info(f"Report exists in DB: {exists}")
    
    # 3. 第一次查詢 (應該從 MOPS 下載)
    logger.info(f"\n=== Step 3: First query (should fetch from MOPS) ===")
    service = get_financial_service()
    statement = await service.get_financial_statement(
        stock_id=stock_id,
        year=year,
        quarter=quarter,
        report_type=report_type,
        format="tree",
    )
    logger.info(f"Got statement: {statement.stock_id} {statement.year}Q{statement.quarter}")
    logger.info(f"Report type: {statement.report_type}")
    logger.info(f"Total items: {len(statement.items)}")
    
    if statement.items:
        # 顯示前幾個項目
        for i, item in enumerate(statement.items[:3]):
            logger.info(f"  - {item.account_name}: {item.value}")
    
    # 4. 檢查 DB 是否有資料了
    logger.info(f"\n=== Step 4: Check DB after first query ===")
    async with get_session() as session:
        repo = FinancialRepository(session)
        exists = await repo.report_exists(stock_id, year, quarter, report_type)
        logger.info(f"Report now exists in DB: {exists}")
    
    # 5. 第二次查詢 (應該從 DB 讀取)
    logger.info(f"\n=== Step 5: Second query (should hit cache) ===")
    statement2 = await service.get_financial_statement(
        stock_id=stock_id,
        year=year,
        quarter=quarter,
        report_type=report_type,
        format="tree",
    )
    logger.info(f"Got statement from cache: {len(statement2.items)} items")
    
    # 6. 測試 use_cache=False
    logger.info(f"\n=== Step 6: Query with use_cache=False (should fetch from MOPS again) ===")
    statement3 = await service.get_financial_statement(
        stock_id=stock_id,
        year=year,
        quarter=quarter,
        report_type=report_type,
        use_cache=False,
    )
    logger.info(f"Got statement after bypass cache: {len(statement3.items)} items")
    
    # 7. 清理
    await close_db()
    logger.info("\n=== Test completed! ===")


if __name__ == "__main__":
    asyncio.run(main())
