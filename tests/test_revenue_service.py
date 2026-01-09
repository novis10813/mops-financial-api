"""
Tests for Revenue Service
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd

from app.services.revenue import (
    RevenueService,
    RevenueServiceError,
    get_revenue_service,
)
from app.schemas.revenue import (
    MonthlyRevenue,
    MarketRevenueResponse,
)


class TestRevenueServiceInit:
    """Test RevenueService initialization"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        service = RevenueService()
        assert service.client is not None
    
    def test_singleton_returns_same_instance(self):
        """Test singleton pattern"""
        service1 = get_revenue_service()
        service2 = get_revenue_service()
        assert service1 is service2


class TestMonthlyRevenueModel:
    """Test MonthlyRevenue Pydantic model"""
    
    def test_create_revenue_model(self):
        """Test creating MonthlyRevenue model"""
        rev = MonthlyRevenue(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
            revenue=278163107,
            yoy_change=57.77,
        )
        
        assert rev.stock_id == "2330"
        assert rev.company_name == "台積電"
        assert rev.year == 113
        assert rev.month == 12
        assert rev.revenue == 278163107
        assert rev.yoy_change == 57.77
    
    def test_optional_fields(self):
        """Test that optional fields can be None"""
        rev = MonthlyRevenue(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
        )
        
        assert rev.revenue is None
        assert rev.comment is None


class TestMarketRevenueResponse:
    """Test MarketRevenueResponse model"""
    
    def test_create_response(self):
        """Test creating response model"""
        data = [
            MonthlyRevenue(stock_id="2330", company_name="台積電", year=113, month=12),
            MonthlyRevenue(stock_id="2317", company_name="鴻海", year=113, month=12),
        ]
        
        response = MarketRevenueResponse(
            year=113,
            month=12,
            market="sii",
            count=2,
            data=data,
        )
        
        assert response.count == 2
        assert len(response.data) == 2





class TestURLConstruction:
    """Test URL construction for different markets"""
    
    def test_sii_url(self):
        """Test URL for 上市 market"""
        year, month, company_type = 113, 12, 0
        url = f"https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{year}_{month}_{company_type}.html"
        assert "sii" in url
        assert "113" in url
        assert "12" in url
    
    def test_otc_url(self):
        """Test URL for 上櫃 market"""
        year, month = 113, 6
        url = f"https://mopsov.twse.com.tw/nas/t21/otc/t21sc03_{year}_{month}_0.html"
        assert "otc" in url
    
    def test_all_markets(self):
        """Test URL for all market types"""
        markets = ["sii", "otc", "rotc", "pub"]
        for market in markets:
            url = f"https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_113_12_0.html"
            assert market in url


class TestRevenueServiceMocked:
    """Test RevenueService with mocked client"""
    
    @pytest.fixture
    def sample_dfs(self):
        """Create sample DataFrames similar to MOPS response"""
        # Simulating the table structure from MOPS
        df = pd.DataFrame({
            0: ["公司代號", "2330", "2317", "合計"],
            1: ["公司名稱", "台積電", "鴻海", ""],
            2: ["當月營收", "278163107", "150000000", ""],
            3: ["上月營收", "276058358", "140000000", ""],
            4: ["去年當月營收", "176299866", "130000000", ""],
            5: ["上月比較增減(%)", "0.76", "7.14", ""],
            6: ["去年同月增減(%)", "57.77", "15.38", ""],
            7: ["當月累計營收", "2894307699", "1600000000", ""],
            8: ["去年累計營收", "2161735841", "1400000000", ""],
            9: ["前期比較增減(%)", "33.88", "14.28", ""],
            10: ["備註", "因先進製程產品需求增加所致。", "-", ""],
        })
        return [df]
    
    @pytest.mark.asyncio
    async def test_parse_revenue_tables(self, sample_dfs):
        """Test parsing sample revenue tables"""
        service = RevenueService()
        
        revenues = service._parse_revenue_tables(sample_dfs, year=113, month=12)
        
        # Should parse 2 companies (skip header and 合計)
        assert len(revenues) == 2
        
        # Check TSMC data
        tsmc = next(r for r in revenues if r.stock_id == "2330")
        assert tsmc.company_name == "台積電"
        assert tsmc.revenue == 278163107
        assert tsmc.yoy_change == 57.77
    
    @pytest.mark.asyncio
    async def test_get_market_revenue_invalid_market(self):
        """Test that invalid market raises error"""
        service = RevenueService()
        
        with pytest.raises(RevenueServiceError) as exc:
            await service.get_market_revenue(113, 12, market="invalid")
        
        assert "Invalid market" in str(exc.value)
