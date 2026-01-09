"""
Tests for Insiders Service (Share Pledging)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd

from app.services.insiders import (
    InsidersService,
    SharePledging,
    PledgingSummary,
    PledgingResponse,
    InsidersServiceError,
    get_insiders_service,
)


class TestInsidersServiceInit:
    """Test InsidersService initialization"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        service = InsidersService()
        assert service.client is not None
    
    def test_singleton_returns_same_instance(self):
        """Test singleton pattern"""
        service1 = get_insiders_service()
        service2 = get_insiders_service()
        assert service1 is service2


class TestSharePledgingModel:
    """Test SharePledging Pydantic model"""
    
    def test_create_pledging_model(self):
        """Test creating SharePledging model"""
        pledging = SharePledging(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
            title="董事長",
            relationship="本人",
            name="魏哲家",
            current_shares=6392834,
            pledged_shares=1600000,
            pledge_ratio=25.02,
        )
        
        assert pledging.stock_id == "2330"
        assert pledging.title == "董事長"
        assert pledging.name == "魏哲家"
        assert pledging.pledge_ratio == 25.02
    
    def test_optional_fields(self):
        """Test that optional fields can be None"""
        pledging = SharePledging(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
            title="獨立董事",
            relationship="本人",
            name="林全",
        )
        
        assert pledging.pledged_shares is None
        assert pledging.pledge_ratio is None


class TestPledgingSummaryModel:
    """Test PledgingSummary model"""
    
    def test_create_summary(self):
        """Test creating summary model"""
        summary = PledgingSummary(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
            total_shares=1689702315,
            total_pledged=1600000,
            total_pledge_ratio=0.09,
        )
        
        assert summary.total_shares == 1689702315
        assert summary.total_pledge_ratio == 0.09


class TestPledgingResponse:
    """Test PledgingResponse model"""
    
    def test_create_response(self):
        """Test creating response with details"""
        details = [
            SharePledging(
                stock_id="2330", company_name="台積電", 
                year=113, month=12, title="董事長", 
                relationship="本人", name="魏哲家"
            ),
        ]
        
        response = PledgingResponse(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=12,
            details=details,
        )
        
        assert len(response.details) == 1
        assert response.summary is None


class TestInsidersServiceParsing:
    """Test parsing logic"""
    
    @pytest.fixture
    def service(self):
        return InsidersService()
    
    def test_parse_int_valid(self, service):
        """Test parsing valid integers"""
        assert service._parse_int("1,234,567") == 1234567
        assert service._parse_int("1000") == 1000
        assert service._parse_int(0) == 0
    
    def test_parse_int_invalid(self, service):
        """Test parsing invalid integers"""
        assert service._parse_int(None) is None
        assert service._parse_int("-") is None
        assert service._parse_int("") is None
    
    def test_parse_percentage_valid(self, service):
        """Test parsing percentage strings"""
        assert service._parse_percentage("25.02%") == 25.02
        assert service._parse_percentage("0.09%") == 0.09
        assert service._parse_percentage("100%") == 100.0
    
    def test_parse_percentage_invalid(self, service):
        """Test parsing invalid percentages"""
        assert service._parse_percentage(None) is None
        assert service._parse_percentage("-") is None
        assert service._parse_percentage("") is None


class TestCompanyNameExtraction:
    """Test company name extraction"""
    
    @pytest.fixture
    def service(self):
        return InsidersService()
    
    def test_extract_company_name(self, service):
        """Test extracting company name from table"""
        df = pd.DataFrame({0: ["2330台灣積體電路製造股份有限公司"]})
        dfs = [df]
        
        name = service._extract_company_name(dfs, "2330")
        assert name == "台灣積體電路製造股份有限公司"
    
    def test_extract_company_name_empty(self, service):
        """Test with empty DataFrames"""
        name = service._extract_company_name([], "2330")
        assert name == ""


class TestHighRiskDetection:
    """Test identifying high-risk pledging"""
    
    def test_high_pledge_ratio_detection(self):
        """Test that high pledge ratios can be identified"""
        details = [
            SharePledging(
                stock_id="TEST", company_name="Test", 
                year=113, month=12, title="董事長",
                relationship="本人", name="A",
                pledged_shares=100000, pledge_ratio=80.0
            ),
            SharePledging(
                stock_id="TEST", company_name="Test", 
                year=113, month=12, title="副總經理",
                relationship="本人", name="B",
                pledged_shares=1000, pledge_ratio=5.0
            ),
        ]
        
        # 找出質押比例 > 50% 的高風險人員
        high_risk = [d for d in details if d.pledge_ratio and d.pledge_ratio > 50]
        
        assert len(high_risk) == 1
        assert high_risk[0].name == "A"
        assert high_risk[0].pledge_ratio == 80.0
