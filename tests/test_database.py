"""
Database Tests

Tests for FinancialRepository using SQLite in-memory database.
"""
import json
import pytest
from decimal import Decimal
from typing import AsyncGenerator

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, JSON, select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.schemas.financial import FinancialStatement, FinancialItem


# ==============================================================================
# Helper: Custom JSON encoder for Decimal
# ==============================================================================

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def serialize_for_json(data: dict) -> dict:
    """Convert Decimal values to float for JSON storage"""
    return json.loads(json.dumps(data, cls=DecimalEncoder))


# ==============================================================================
# SQLite-compatible models (prefixed with DB to avoid pytest collection)
# ==============================================================================

class DBBase(DeclarativeBase):
    """SQLAlchemy declarative base for tests"""
    pass


class DBCompany(DBBase):
    """SQLite compatible Company model"""
    __tablename__ = "companies"
    
    stock_id = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    industry = Column(String(50))
    market = Column(String(20))
    updated_at = Column(DateTime)
    
    reports = relationship("DBFinancialReport", back_populates="company")


class DBFinancialReport(DBBase):
    """SQLite compatible FinancialReport model"""
    __tablename__ = "financial_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(String(10), ForeignKey("companies.stock_id"), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    report_type = Column(String(30), nullable=False)
    full_data = Column(JSON, nullable=True)
    fetched_at = Column(DateTime)
    source = Column(String(50), default="mops")
    is_standalone = Column(Boolean, default=False)
    
    company = relationship("DBCompany", back_populates="reports")
    facts = relationship("DBFinancialFact", back_populates="report", cascade="all, delete-orphan")


class DBFinancialFact(DBBase):
    """SQLite compatible FinancialFact model"""
    __tablename__ = "financial_facts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("financial_reports.id", ondelete="CASCADE"), nullable=False)
    concept = Column(String(100), nullable=False)
    label_zh = Column(String(200))
    label_en = Column(String(200))
    value = Column(Numeric(20, 4), nullable=True)
    level = Column(Integer, default=0)
    weight = Column(Numeric(3, 1), default=1.0)
    
    report = relationship("DBFinancialReport", back_populates="facts")


# ==============================================================================
# Repository for testing (adapted for SQLite)
# ==============================================================================

class InMemoryFinancialRepository:
    """
    Test version of FinancialRepository using SQLite-compatible models
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_company(
        self,
        stock_id: str,
        name: str,
        name_en: str = None,
    ) -> DBCompany:
        """新增或更新公司"""
        result = await self.session.execute(
            select(DBCompany).where(DBCompany.stock_id == stock_id)
        )
        company = result.scalar_one_or_none()
        
        if company:
            company.name = name
            if name_en:
                company.name_en = name_en
        else:
            company = DBCompany(stock_id=stock_id, name=name, name_en=name_en)
            self.session.add(company)
        
        await self.session.flush()
        return company
    
    async def save_report(self, statement: FinancialStatement) -> int:
        """儲存報表"""
        # Ensure company exists
        await self.upsert_company(
            stock_id=statement.stock_id,
            name=statement.company_name or f"Company {statement.stock_id}",
        )
        
        # Check if report exists
        result = await self.session.execute(
            select(DBFinancialReport).where(
                DBFinancialReport.stock_id == statement.stock_id,
                DBFinancialReport.year == statement.year,
                DBFinancialReport.quarter == statement.quarter,
                DBFinancialReport.report_type == statement.report_type,
            )
        )
        existing = result.scalar_one_or_none()
        
        # Serialize with Decimal handling
        full_data = serialize_for_json(statement.model_dump())
        
        if existing:
            existing.full_data = full_data
            report = existing
        else:
            report = DBFinancialReport(
                stock_id=statement.stock_id,
                year=statement.year,
                quarter=statement.quarter or 4,
                report_type=statement.report_type,
                full_data=full_data,
                is_standalone=statement.is_standalone,
            )
            self.session.add(report)
        
        await self.session.flush()
        
        # Save facts
        facts = self._extract_facts(statement.items, report.id)
        for fact in facts:
            self.session.add(fact)
        
        await self.session.commit()
        return report.id
    
    async def get_report(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
    ) -> FinancialStatement | None:
        """取得報表"""
        result = await self.session.execute(
            select(DBFinancialReport).where(
                DBFinancialReport.stock_id == stock_id,
                DBFinancialReport.year == year,
                DBFinancialReport.quarter == quarter,
                DBFinancialReport.report_type == report_type,
            )
        )
        report = result.scalar_one_or_none()
        
        if not report or not report.full_data:
            return None
        
        return FinancialStatement.model_validate(report.full_data)
    
    async def report_exists(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
    ) -> bool:
        """檢查報表是否存在"""
        result = await self.session.execute(
            select(func.count()).select_from(DBFinancialReport).where(
                DBFinancialReport.stock_id == stock_id,
                DBFinancialReport.year == year,
                DBFinancialReport.quarter == quarter,
                DBFinancialReport.report_type == report_type,
            )
        )
        return result.scalar() > 0
    
    def _extract_facts(self, items: list[FinancialItem], report_id: int) -> list[DBFinancialFact]:
        """提取 facts"""
        facts = []
        for item in items:
            fact = DBFinancialFact(
                report_id=report_id,
                concept=item.account_code,
                label_zh=item.account_name,
                label_en=item.account_name_en,
                value=item.value,
                level=item.level,
                weight=Decimal(str(item.weight)),
            )
            facts.append(fact)
            facts.extend(self._extract_facts(item.children, report_id))
        return facts


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
async def db_engine():
    """Create in-memory SQLite engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(DBBase.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test session"""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def repo(db_session) -> InMemoryFinancialRepository:
    """Create test repository"""
    return InMemoryFinancialRepository(db_session)


# ==============================================================================
# Sample Data
# ==============================================================================

def create_sample_statement() -> FinancialStatement:
    """Create a sample financial statement for testing"""
    return FinancialStatement(
        stock_id="2330",
        company_name="台積電",
        year=113,
        quarter=3,
        report_type="balance_sheet",
        is_standalone=False,
        items=[
            FinancialItem(
                account_code="Assets",
                account_name="資產總計",
                account_name_en="Total Assets",
                value=Decimal("1000000"),
                weight=1.0,
                level=0,
                children=[
                    FinancialItem(
                        account_code="CurrentAssets",
                        account_name="流動資產",
                        account_name_en="Current Assets",
                        value=Decimal("400000"),
                        weight=1.0,
                        level=1,
                        children=[],
                    ),
                    FinancialItem(
                        account_code="NonCurrentAssets",
                        account_name="非流動資產",
                        account_name_en="Non-current Assets",
                        value=Decimal("600000"),
                        weight=1.0,
                        level=1,
                        children=[],
                    ),
                ],
            ),
        ],
    )


# ==============================================================================
# Tests
# ==============================================================================

class TestRepositorySaveAndGet:
    """Test save and retrieve operations"""
    
    @pytest.mark.asyncio
    async def test_save_report(self, repo):
        """Test saving a report"""
        statement = create_sample_statement()
        
        report_id = await repo.save_report(statement)
        
        assert report_id is not None
        assert report_id > 0
    
    @pytest.mark.asyncio
    async def test_get_report_after_save(self, repo):
        """Test retrieving a saved report"""
        statement = create_sample_statement()
        await repo.save_report(statement)
        
        retrieved = await repo.get_report(
            stock_id="2330",
            year=113,
            quarter=3,
            report_type="balance_sheet",
        )
        
        assert retrieved is not None
        assert retrieved.stock_id == "2330"
        assert retrieved.year == 113
        assert retrieved.quarter == 3
        assert retrieved.report_type == "balance_sheet"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_report(self, repo):
        """Test retrieving a report that doesn't exist"""
        retrieved = await repo.get_report(
            stock_id="9999",
            year=999,
            quarter=1,
            report_type="balance_sheet",
        )
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_report_exists_true(self, repo):
        """Test report_exists returns True for existing report"""
        statement = create_sample_statement()
        await repo.save_report(statement)
        
        exists = await repo.report_exists(
            stock_id="2330",
            year=113,
            quarter=3,
            report_type="balance_sheet",
        )
        
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_report_exists_false(self, repo):
        """Test report_exists returns False for non-existing report"""
        exists = await repo.report_exists(
            stock_id="9999",
            year=999,
            quarter=1,
            report_type="balance_sheet",
        )
        
        assert exists is False


class TestRepositoryUpdate:
    """Test update operations"""
    
    @pytest.mark.asyncio
    async def test_update_existing_report(self, repo):
        """Test updating an existing report"""
        # Save initial version
        statement = create_sample_statement()
        await repo.save_report(statement)
        
        # Update with new data
        statement.items[0].value = Decimal("2000000")
        await repo.save_report(statement)
        
        # Retrieve and verify
        retrieved = await repo.get_report(
            stock_id="2330",
            year=113,
            quarter=3,
            report_type="balance_sheet",
        )
        
        assert retrieved is not None
        # Note: value is stored as float in JSON, so compare as float
        assert float(retrieved.items[0].value) == 2000000.0


class TestRepositoryCompany:
    """Test company operations"""
    
    @pytest.mark.asyncio
    async def test_upsert_company_create(self, repo):
        """Test creating a new company"""
        company = await repo.upsert_company(
            stock_id="2330",
            name="台積電",
            name_en="TSMC",
        )
        
        assert company.stock_id == "2330"
        assert company.name == "台積電"
    
    @pytest.mark.asyncio
    async def test_upsert_company_update(self, repo):
        """Test updating an existing company"""
        # Create
        await repo.upsert_company(stock_id="2330", name="台積電")
        
        # Update
        company = await repo.upsert_company(
            stock_id="2330",
            name="台灣積體電路製造",
            name_en="Taiwan Semiconductor",
        )
        
        assert company.name == "台灣積體電路製造"
        assert company.name_en == "Taiwan Semiconductor"
