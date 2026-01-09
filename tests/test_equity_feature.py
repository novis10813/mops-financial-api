
import pytest
import json
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, JSON, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.financial import FinancialStatement, FinancialItem

# ==============================================================================
# 1. Database Access Tests (Repository Layer)
# ==============================================================================

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def serialize_for_json(data: dict) -> dict:
    return json.loads(json.dumps(data, cls=DecimalEncoder))

# Define Local DB Models to avoid import conflicts/coupling with test_database.py
class LocalDBBase(DeclarativeBase):
    pass

class DBCompany(LocalDBBase):
    __tablename__ = "companies"
    stock_id = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    reports = relationship("DBFinancialReport", back_populates="company")

class DBFinancialReport(LocalDBBase):
    __tablename__ = "financial_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(String(10), ForeignKey("companies.stock_id"), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    report_type = Column(String(30), nullable=False)
    full_data = Column(JSON, nullable=True)
    is_standalone = Column(Boolean, default=False)
    company = relationship("DBCompany", back_populates="reports")
    facts = relationship("DBFinancialFact", back_populates="report", cascade="all, delete-orphan")

class DBFinancialFact(LocalDBBase):
    __tablename__ = "financial_facts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("financial_reports.id", ondelete="CASCADE"), nullable=False)
    concept = Column(String(100), nullable=False)
    value = Column(Numeric(20, 4), nullable=True)
    report = relationship("DBFinancialReport", back_populates="facts")

class InMemoryFinancialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_company(self, stock_id: str, name: str):
        result = await self.session.execute(select(DBCompany).where(DBCompany.stock_id == stock_id))
        company = result.scalar_one_or_none()
        if not company:
            company = DBCompany(stock_id=stock_id, name=name)
            self.session.add(company)
        return company

    async def save_report(self, statement: FinancialStatement) -> int:
        await self.upsert_company(statement.stock_id, statement.company_name or f"Co {statement.stock_id}")
        
        full_data = serialize_for_json(statement.model_dump())
        
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
        return report.id

    async def get_report(self, stock_id: str, year: int, quarter: int, report_type: str) -> FinancialStatement | None:
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

@pytest.fixture
async def db_session_local():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(LocalDBBase.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest.fixture
async def repo_local(db_session_local):
    return InMemoryFinancialRepository(db_session_local)

@pytest.mark.asyncio
async def test_db_save_and_get_equity_statement(repo_local):
    """Test saving and retrieving an Equity Statement (Database Verification)"""
    statement = FinancialStatement(
        stock_id="2330",
        company_name="TSMC",
        year=113,
        quarter=2,
        report_type="equity_statement",
        items=[
            FinancialItem(
                account_code="Equity",
                account_name="權益總計",
                value=Decimal("500000"),
                level=0,
                children=[]
            )
        ]
    )
    
    # Save
    report_id = await repo_local.save_report(statement)
    assert report_id > 0
    
    # Retrieve
    retrieved = await repo_local.get_report("2330", 113, 2, "equity_statement")
    assert retrieved is not None
    assert retrieved.report_type == "equity_statement"
    assert retrieved.items[0].account_code == "Equity"
    assert float(retrieved.items[0].value) == 500000.0


# ==============================================================================
# 2. Field Validation Tests (Router/API Layer)
# ==============================================================================

client = TestClient(app)

def test_get_equity_statement_validation_success():
    """Test valid parameters for equality statement"""
    # Mock service to avoid DB/Network calls
    with patch("app.routers.financial.get_financial_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock return value
        mock_service.get_financial_statement.return_value = FinancialStatement(
            stock_id="2330",
            year=113,
            quarter=3,
            report_type="equity_statement",
            items=[]
        )
        
        response = client.get("/api/v1/financial/2330/equity-statement?year=113&quarter=3")
        
        assert response.status_code == 200
        assert response.json()["report_type"] == "equity_statement"
        
        # Verify arguments passed to service
        mock_service.get_financial_statement.assert_called_with(
            stock_id="2330",
            year=113,
            quarter=3,
            report_type="equity_statement",
            format="tree"
        )

def test_get_equity_statement_validation_invalid_quarter():
    """Test invalid quarter (must be 1-4)"""
    response = client.get("/api/v1/financial/2330/equity-statement?year=113&quarter=5")
    assert response.status_code == 422  # Validation Error

def test_get_equity_statement_validation_invalid_quarter_type():
    """Test invalid quarter type"""
    response = client.get("/api/v1/financial/2330/equity-statement?year=113&quarter=Q1")
    assert response.status_code == 422

def test_get_equity_statement_validation_missing_year():
    """Test missing required year"""
    response = client.get("/api/v1/financial/2330/equity-statement?quarter=1")
    assert response.status_code == 422

def test_simplified_statement_validation_equity():
    """Test simplified statement endpoint accepts 'equity_statement'"""
    with patch("app.routers.financial.get_financial_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_simplified_statement.return_value = {
            "stock_id": "2330",
            "year": 113,
            "statement_type": "equity_statement",
            "items": []
        }
        
        response = client.get("/api/v1/financial/2330/simplified/equity_statement?year=113")
        assert response.status_code == 200
        assert response.json()["statement_type"] == "equity_statement"

def test_simplified_statement_validation_invalid_type():
    """Test simplified statement endpoint rejects invalid type"""
    response = client.get("/api/v1/financial/2330/simplified/invalid_type?year=113")
    assert response.status_code == 400  # Custom HTTPException
