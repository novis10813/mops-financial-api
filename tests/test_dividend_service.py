"""
Tests for Dividend Service
"""
import pytest

from app.services.dividend import (
    DividendService,
    DividendRecord,
    DividendSummary,
    DividendResponse,
    DividendServiceError,
    get_dividend_service,
)


class TestDividendServiceInit:
    """Test DividendService initialization"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        service = DividendService()
        assert service.client is not None
    
    def test_singleton_returns_same_instance(self):
        """Test singleton pattern"""
        service1 = get_dividend_service()
        service2 = get_dividend_service()
        assert service1 is service2


class TestDividendRecordModel:
    """Test DividendRecord Pydantic model"""
    
    def test_create_dividend_record(self):
        """Test creating DividendRecord model"""
        record = DividendRecord(
            stock_id="2330",
            company_name="台積電",
            year=112,
            quarter=1,
            cash_dividend=3.0,
            stock_dividend=0.0,
            total_dividend=3.0,
            board_resolution_date="112/05/09",
        )
        
        assert record.stock_id == "2330"
        assert record.year == 112
        assert record.quarter == 1
        assert record.cash_dividend == 3.0
    
    def test_annual_dividend(self):
        """Test creating annual dividend record (no quarter)"""
        record = DividendRecord(
            stock_id="2317",
            company_name="鴻海",
            year=112,
            quarter=None,  # Annual dividend
            cash_dividend=5.3,
        )
        
        assert record.quarter is None
    
    def test_optional_fields(self):
        """Test that optional fields can be None"""
        record = DividendRecord(
            stock_id="2330",
            company_name="台積電",
            year=112,
        )
        
        assert record.cash_dividend is None
        assert record.stock_dividend is None


class TestDividendSummaryModel:
    """Test DividendSummary model"""
    
    def test_create_summary(self):
        """Test creating summary model"""
        summary = DividendSummary(
            stock_id="2330",
            company_name="台積電",
            year=112,
            total_cash_dividend=13.0,
            total_stock_dividend=0.0,
            total_dividend=13.0,
        )
        
        assert summary.total_cash_dividend == 13.0
        assert summary.year == 112
    
    def test_quarterly_dividends_list(self):
        """Test summary with quarterly dividends"""
        records = [
            DividendRecord(stock_id="2330", company_name="台積電", year=112, quarter=q, cash_dividend=3.0)
            for q in [1, 2, 3, 4]
        ]
        
        summary = DividendSummary(
            stock_id="2330",
            company_name="台積電",
            year=112,
            total_cash_dividend=12.0,
            quarterly_dividends=records,
        )
        
        assert len(summary.quarterly_dividends) == 4


class TestDividendResponse:
    """Test DividendResponse model"""
    
    def test_create_response(self):
        """Test creating response model"""
        records = [
            DividendRecord(stock_id="2330", company_name="台積電", year=112, quarter=1),
        ]
        
        response = DividendResponse(
            stock_id="2330",
            company_name="台積電",
            year_start=112,
            year_end=112,
            count=1,
            records=records,
        )
        
        assert response.count == 1


class TestDividendServiceParsing:
    """Test parsing logic"""
    
    @pytest.fixture
    def service(self):
        return DividendService()
    
    def test_extract_year(self, service):
        """Test extracting year from period string"""
        assert service._extract_year("112年10/01~112年12/31") == 112
        assert service._extract_year("111年度") == 111
        assert service._extract_year("No year") is None
    
    def test_extract_quarter(self, service):
        """Test extracting quarter from period string"""
        assert service._extract_quarter("112/01/01~112/03/31") == 1
        assert service._extract_quarter("112/04/01~112/06/30") == 2
        assert service._extract_quarter("112/07/01~112/09/30") == 3
        assert service._extract_quarter("112/10/01~112/12/31") == 4
        assert service._extract_quarter("112年度") is None
    
    def test_parse_float_valid(self, service):
        """Test parsing valid floats"""
        assert service._parse_float("3.49978969") == 3.4998
        assert service._parse_float("5.00000000") == 5.0
        assert service._parse_float("1,234.56") == 1234.56
    
    def test_parse_float_invalid(self, service):
        """Test parsing invalid floats"""
        assert service._parse_float(None) is None
        assert service._parse_float("-") is None
        assert service._parse_float("0.0") is None


class TestYieldCalculation:
    """Test dividend yield calculation scenarios"""
    
    def test_calculate_yield(self):
        """Test calculating dividend yield"""
        # 台積電 112年 現金股利約13元，股價約 500 元
        cash_dividend = 13.0
        stock_price = 500.0
        
        dividend_yield = (cash_dividend / stock_price) * 100
        
        assert 2.0 < dividend_yield < 3.0  # ~2.6%
    
    def test_quarterly_yield(self):
        """Test calculating yield from quarterly dividends"""
        quarterly_dividends = [3.0, 3.0, 3.5, 3.5]  # Q1-Q4
        total = sum(quarterly_dividends)
        
        assert total == 13.0
