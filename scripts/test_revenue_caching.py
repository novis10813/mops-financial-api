#!/usr/bin/env python
"""
測試 RevenueService 的 DB 快取功能

使用方式:
  MOPS_POSTGRES_HOST=localhost MOPS_POSTGRES_PORT=5433 MOPS_POSTGRES_PASSWORD=testpassword \
    uv run python scripts/test_revenue_caching.py
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    from app.db.connection import init_db, close_db, get_session
    from app.db.repository import RevenueRepository
    from app.services.revenue import get_revenue_service
    
    # 1. 初始化資料庫 (建立 tables)
    logger.info("=== Step 1: Initializing database ===")
    await init_db()
    logger.info("Database initialized successfully!")
    
    # 2. 檢查目前 DB 中有多少營收資料
    logger.info("\n=== Step 2: Check current DB state ===")
    async with get_session() as session:
        repo = RevenueRepository(session)
        count = await repo.count_revenues(113, 12, "sii")
        logger.info(f"Current records in DB for 113/12 sii: {count}")
    
    # 3. 第一次查詢 (應該從 MOPS 爬取)
    logger.info("\n=== Step 3: First query (should fetch from MOPS) ===")
    service = get_revenue_service()
    revenues = await service.get_market_revenue(113, 12, "sii")
    logger.info(f"Got {len(revenues)} records")
    if revenues:
        logger.info(f"Sample: {revenues[0].stock_id} - {revenues[0].company_name}: {revenues[0].revenue}")
    
    # 4. 檢查 DB 是否有資料了
    logger.info("\n=== Step 4: Check DB after first query ===")
    async with get_session() as session:
        repo = RevenueRepository(session)
        count = await repo.count_revenues(113, 12, "sii")
        logger.info(f"Records in DB after query: {count}")
    
    # 5. 第二次查詢 (應該從 DB 讀取)
    logger.info("\n=== Step 5: Second query (should hit cache) ===")
    revenues2 = await service.get_market_revenue(113, 12, "sii")
    logger.info(f"Got {len(revenues2)} records from cache")
    
    # 6. 測試 force_refresh
    logger.info("\n=== Step 6: Force refresh (should fetch from MOPS again) ===")
    revenues3 = await service.get_market_revenue(113, 12, "sii", force_refresh=True)
    logger.info(f"Got {len(revenues3)} records after force refresh")
    
    # 7. 清理
    await close_db()
    logger.info("\n=== Test completed! ===")


if __name__ == "__main__":
    asyncio.run(main())
