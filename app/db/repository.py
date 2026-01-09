"""
Financial Repository

Data access layer for financial reports storage and retrieval
"""
import logging
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Company, FinancialReport, FinancialFact, MonthlyRevenue as MonthlyRevenueModel
from app.schemas.financial import FinancialStatement, FinancialItem
from app.services.revenue import MonthlyRevenue as MonthlyRevenueSchema


logger = logging.getLogger(__name__)


class FinancialRepository:
    """
    財務報表資料存取層
    
    提供報表的 CRUD 操作和快取查詢
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ==================== Company ====================
    
    async def upsert_company(
        self,
        stock_id: str,
        name: str,
        name_en: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Company:
        """
        新增或更新公司資料
        """
        stmt = insert(Company).values(
            stock_id=stock_id,
            name=name,
            name_en=name_en,
            industry=industry,
            market=market,
        ).on_conflict_do_update(
            index_elements=["stock_id"],
            set_={
                "name": name,
                "name_en": name_en,
                "industry": industry,
                "market": market,
            }
        ).returning(Company)
        
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    # ==================== Financial Report ====================
    
    async def get_report(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
    ) -> Optional[FinancialStatement]:
        """
        從資料庫取得報表
        
        Returns:
            FinancialStatement if found, None otherwise
        """
        # 查詢報表
        stmt = select(FinancialReport).where(
            and_(
                FinancialReport.stock_id == stock_id,
                FinancialReport.year == year,
                FinancialReport.quarter == quarter,
                FinancialReport.report_type == report_type,
            )
        )
        
        result = await self.session.execute(stmt)
        report = result.scalar_one_or_none()
        
        if not report:
            return None
        
        # 從 full_data 重建 FinancialStatement
        if report.full_data:
            return FinancialStatement.model_validate(report.full_data)
        
        # Fallback: 從 facts 重建（如果沒有 full_data）
        return await self._build_statement_from_facts(report)
    
    async def save_report(
        self,
        statement: FinancialStatement,
    ) -> int:
        """
        儲存報表到資料庫
        
        Args:
            statement: 財務報表
            
        Returns:
            report_id
        """
        # 1. 確保公司存在
        await self.upsert_company(
            stock_id=statement.stock_id,
            name=statement.company_name or statement.stock_id,
        )
        
        # 2. 建立或更新報表記錄
        stmt = insert(FinancialReport).values(
            stock_id=statement.stock_id,
            year=statement.year,
            quarter=statement.quarter or 4,
            report_type=statement.report_type,
            full_data=statement.model_dump(mode="json"),
            is_standalone=statement.is_standalone,
        ).on_conflict_do_update(
            constraint="uq_report_identity",
            set_={
                "full_data": statement.model_dump(mode="json"),
                "is_standalone": statement.is_standalone,
            }
        ).returning(FinancialReport.id)
        
        result = await self.session.execute(stmt)
        report_id = result.scalar_one()
        
        # 3. 刪除舊的 facts
        from sqlalchemy import delete
        await self.session.execute(
            delete(FinancialFact).where(FinancialFact.report_id == report_id)
        )
        
        # 4. 插入新的 facts
        facts = self._extract_facts(statement.items, report_id)
        if facts:
            await self.session.execute(insert(FinancialFact), facts)
        
        logger.info(f"Saved report {statement.stock_id} {statement.year}Q{statement.quarter} {statement.report_type} with {len(facts)} facts")
        
        return report_id
    
    async def report_exists(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
    ) -> bool:
        """
        檢查報表是否已存在
        """
        stmt = select(FinancialReport.id).where(
            and_(
                FinancialReport.stock_id == stock_id,
                FinancialReport.year == year,
                FinancialReport.quarter == quarter,
                FinancialReport.report_type == report_type,
            )
        ).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    # ==================== Financial Facts ====================
    
    async def get_fact_value(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
        concept: str,
    ) -> Optional[Decimal]:
        """
        快速查詢單一科目數值
        
        Example:
            revenue = await repo.get_fact_value("2330", 113, 3, "income_statement", "Revenue")
        """
        stmt = (
            select(FinancialFact.value)
            .join(FinancialReport)
            .where(
                and_(
                    FinancialReport.stock_id == stock_id,
                    FinancialReport.year == year,
                    FinancialReport.quarter == quarter,
                    FinancialReport.report_type == report_type,
                    FinancialFact.concept == concept,
                )
            )
            .limit(1)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_available_reports(
        self,
        stock_id: str,
    ) -> List[dict]:
        """
        列出某公司所有可用報表
        """
        stmt = (
            select(
                FinancialReport.year,
                FinancialReport.quarter,
                FinancialReport.report_type,
                FinancialReport.fetched_at,
            )
            .where(FinancialReport.stock_id == stock_id)
            .order_by(
                FinancialReport.year.desc(),
                FinancialReport.quarter.desc(),
            )
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        return [
            {
                "year": row.year,
                "quarter": row.quarter,
                "report_type": row.report_type,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rows
        ]
    
    # ==================== Private Helpers ====================
    
    def _extract_facts(
        self,
        items: List[FinancialItem],
        report_id: int,
        level: int = 0,
    ) -> List[dict]:
        """
        遞迴提取所有財務項目為扁平 facts
        """
        facts = []
        
        for item in items:
            if item.value is not None:
                facts.append({
                    "report_id": report_id,
                    "concept": item.account_code,
                    "label_zh": item.account_name,
                    "label_en": item.account_name_en,
                    "value": item.value,
                    "level": level,
                    "weight": item.weight,
                })
            
            # 遞迴處理子項目
            if item.children:
                facts.extend(self._extract_facts(item.children, report_id, level + 1))
        
        return facts
    
    async def _build_statement_from_facts(
        self,
        report: FinancialReport,
    ) -> FinancialStatement:
        """
        從 facts 重建 FinancialStatement (fallback)
        """
        # 查詢所有 facts
        stmt = select(FinancialFact).where(
            FinancialFact.report_id == report.id
        )
        result = await self.session.execute(stmt)
        facts = result.scalars().all()
        
        # 建立扁平結構
        items = [
            FinancialItem(
                account_code=f.concept,
                account_name=f.label_zh or f.concept,
                account_name_en=f.label_en,
                value=f.value,
                weight=float(f.weight) if f.weight else 1.0,
                level=f.level or 0,
                children=[],
            )
            for f in facts
        ]
        
        return FinancialStatement(
            stock_id=report.stock_id,
            year=report.year,
            quarter=report.quarter,
            report_type=report.report_type,
            is_standalone=report.is_standalone,
            items=items,
        )


class RevenueRepository:
    """
    月營收資料存取層
    
    提供月營收的 CRUD 操作和快取查詢
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_revenues(
        self,
        revenues: List[MonthlyRevenueSchema],
        market: str = "sii",
    ) -> int:
        """
        批次儲存月營收資料 (upsert)
        
        Args:
            revenues: 月營收資料列表
            market: 市場類型
            
        Returns:
            更新的記錄數
        """
        if not revenues:
            return 0
        
        count = 0
        for rev in revenues:
            stmt = insert(MonthlyRevenueModel).values(
                stock_id=rev.stock_id,
                company_name=rev.company_name,
                year=rev.year,
                month=rev.month,
                market=market,
                revenue=rev.revenue,
                revenue_last_month=rev.revenue_last_month,
                revenue_last_year=rev.revenue_last_year,
                mom_change=rev.mom_change,
                yoy_change=rev.yoy_change,
                accumulated_revenue=rev.accumulated_revenue,
                accumulated_last_year=rev.accumulated_last_year,
                accumulated_yoy_change=rev.accumulated_yoy_change,
                comment=rev.comment,
            ).on_conflict_do_update(
                constraint="uq_revenue_identity",
                set_={
                    "company_name": rev.company_name,
                    "revenue": rev.revenue,
                    "revenue_last_month": rev.revenue_last_month,
                    "revenue_last_year": rev.revenue_last_year,
                    "mom_change": rev.mom_change,
                    "yoy_change": rev.yoy_change,
                    "accumulated_revenue": rev.accumulated_revenue,
                    "accumulated_last_year": rev.accumulated_last_year,
                    "accumulated_yoy_change": rev.accumulated_yoy_change,
                    "comment": rev.comment,
                }
            )
            await self.session.execute(stmt)
            count += 1
        
        logger.info(f"Saved {count} revenue records for {revenues[0].year}/{revenues[0].month}")
        return count
    
    async def get_revenue(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> Optional[MonthlyRevenueSchema]:
        """
        取得單一公司月營收
        """
        stmt = select(MonthlyRevenueModel).where(
            and_(
                MonthlyRevenueModel.stock_id == stock_id,
                MonthlyRevenueModel.year == year,
                MonthlyRevenueModel.month == month,
                MonthlyRevenueModel.market == market,
            )
        )
        
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            return None
        
        return self._model_to_schema(record)
    
    async def get_market_revenues(
        self,
        year: int,
        month: int,
        market: str = "sii",
    ) -> List[MonthlyRevenueSchema]:
        """
        取得全市場月營收
        """
        stmt = select(MonthlyRevenueModel).where(
            and_(
                MonthlyRevenueModel.year == year,
                MonthlyRevenueModel.month == month,
                MonthlyRevenueModel.market == market,
            )
        ).order_by(MonthlyRevenueModel.stock_id)
        
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        
        return [self._model_to_schema(r) for r in records]
    
    async def revenue_exists(
        self,
        year: int,
        month: int,
        market: str = "sii",
    ) -> bool:
        """
        檢查特定月份的營收資料是否已存在
        """
        stmt = select(MonthlyRevenueModel.id).where(
            and_(
                MonthlyRevenueModel.year == year,
                MonthlyRevenueModel.month == month,
                MonthlyRevenueModel.market == market,
            )
        ).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def count_revenues(
        self,
        year: int,
        month: int,
        market: str = "sii",
    ) -> int:
        """
        計算特定月份的營收記錄數
        """
        from sqlalchemy import func
        stmt = select(func.count()).where(
            and_(
                MonthlyRevenueModel.year == year,
                MonthlyRevenueModel.month == month,
                MonthlyRevenueModel.market == market,
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
    
    def _model_to_schema(self, record: MonthlyRevenueModel) -> MonthlyRevenueSchema:
        """Convert database model to Pydantic schema"""
        return MonthlyRevenueSchema(
            stock_id=record.stock_id,
            company_name=record.company_name or "",
            year=record.year,
            month=record.month,
            revenue=int(record.revenue) if record.revenue else None,
            revenue_last_month=int(record.revenue_last_month) if record.revenue_last_month else None,
            revenue_last_year=int(record.revenue_last_year) if record.revenue_last_year else None,
            mom_change=float(record.mom_change) if record.mom_change else None,
            yoy_change=float(record.yoy_change) if record.yoy_change else None,
            accumulated_revenue=int(record.accumulated_revenue) if record.accumulated_revenue else None,
            accumulated_last_year=int(record.accumulated_last_year) if record.accumulated_last_year else None,
            accumulated_yoy_change=float(record.accumulated_yoy_change) if record.accumulated_yoy_change else None,
            comment=record.comment,
        )
