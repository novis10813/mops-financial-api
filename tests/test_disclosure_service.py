"""
Tests for Disclosure Service (Funds Lending & Endorsement/Guarantee)
"""
import pytest

from app.services.disclosure import (
    DisclosureService,
    FundsLending,
    EndorsementGuarantee,
    CrossCompanyGuarantee,
    ChinaGuarantee,
    DisclosureResponse,
    DisclosureServiceError,
    get_disclosure_service,
)


class TestDisclosureServiceInit:
    """Test DisclosureService initialization"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        service = DisclosureService()
        assert service.client is not None
    
    def test_singleton_returns_same_instance(self):
        """Test singleton pattern"""
        service1 = get_disclosure_service()
        service2 = get_disclosure_service()
        assert service1 is service2


class TestFundsLendingModel:
    """Test FundsLending Pydantic model"""
    
    def test_create_funds_lending(self):
        """Test creating FundsLending model"""
        fl = FundsLending(
            entity="本公司",
            has_balance=True,
            current_month=5000000,
            previous_month=5000000,
            max_limit=593999872,
        )
        
        assert fl.entity == "本公司"
        assert fl.has_balance is True
        assert fl.current_month == 5000000
        assert fl.max_limit == 593999872
    
    def test_no_balance(self):
        """Test company with no lending balance"""
        fl = FundsLending(
            entity="本公司",
            has_balance=False,
        )
        
        assert fl.has_balance is False
        assert fl.current_month is None


class TestEndorsementGuaranteeModel:
    """Test EndorsementGuarantee Pydantic model"""
    
    def test_create_endorsement(self):
        """Test creating EndorsementGuarantee model"""
        eg = EndorsementGuarantee(
            entity="本公司",
            has_balance=True,
            monthly_change=-3508687,
            accumulated_balance=198915488,
            max_limit=1484999679,
        )
        
        assert eg.entity == "本公司"
        assert eg.monthly_change == -3508687  # 負數=減少
        assert eg.accumulated_balance == 198915488


class TestCrossCompanyGuarantee:
    """Test CrossCompanyGuarantee model"""
    
    def test_create_cross_company(self):
        """Test creating cross-company guarantee"""
        cc = CrossCompanyGuarantee(
            parent_to_subsidiary=198915488,
            subsidiary_to_parent=0,
        )
        
        assert cc.parent_to_subsidiary == 198915488
        assert cc.subsidiary_to_parent == 0


class TestChinaGuarantee:
    """Test ChinaGuarantee model"""
    
    def test_create_china_guarantee(self):
        """Test creating China guarantee"""
        cg = ChinaGuarantee(
            entity="子公司",
            has_balance=True,
            monthly_change=-451751,
            accumulated_balance=7359563,
        )
        
        assert cg.entity == "子公司"
        assert cg.accumulated_balance == 7359563


class TestDisclosureResponse:
    """Test DisclosureResponse model"""
    
    def test_create_response(self):
        """Test creating complete response"""
        response = DisclosureResponse(
            stock_id="2317",
            company_name="鴻海",
            year=112,
            month=12,
            funds_lending=[
                FundsLending(entity="本公司", has_balance=True, current_month=5000000)
            ],
            endorsement_guarantee=[
                EndorsementGuarantee(entity="本公司", has_balance=True, accumulated_balance=198915488)
            ],
        )
        
        assert response.stock_id == "2317"
        assert len(response.funds_lending) == 1
        assert len(response.endorsement_guarantee) == 1


class TestDisclosureServiceParsing:
    """Test parsing logic"""
    
    @pytest.fixture
    def service(self):
        return DisclosureService()
    
    def test_parse_int_valid(self, service):
        """Test parsing valid integers"""
        assert service._parse_int("5,000,000") == 5000000
        assert service._parse_int("1000") == 1000
        assert service._parse_int("-3508687") == -3508687
    
    def test_parse_int_invalid(self, service):
        """Test parsing invalid integers"""
        assert service._parse_int(None) is None
        assert service._parse_int("-") is None
        assert service._parse_int("") is None


class TestRiskAssessment:
    """Test risk assessment scenarios"""
    
    def test_high_guarantee_ratio(self):
        """Test identifying high guarantee-to-limit ratio"""
        eg = EndorsementGuarantee(
            entity="本公司",
            has_balance=True,
            accumulated_balance=1000000000,  # 10億
            max_limit=1100000000,           # 11億限額
        )
        
        # 使用率 = 餘額 / 限額
        usage_ratio = eg.accumulated_balance / eg.max_limit
        
        assert usage_ratio > 0.9  # 超過 90% 使用率
    
    def test_guarantee_to_equity(self):
        """Test calculating guarantee to equity ratio"""
        # 假設公司淨值 1000 億
        equity = 100_000_000_000  # 千元 = 1000億
        guarantee = 198_915_488   # 約 1.99 億
        
        ratio = guarantee / equity * 100
        
        assert ratio < 1  # 低於 1% 是健康的
