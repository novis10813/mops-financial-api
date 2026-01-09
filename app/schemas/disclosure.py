from typing import Optional, List
from pydantic import BaseModel


class FundsLending(BaseModel):
    """資金貸放資訊"""
    entity: str                          # 本公司/各子公司
    has_balance: bool                    # 是否有餘額
    current_month: Optional[int] = None  # 本月餘額 (千元)
    previous_month: Optional[int] = None # 上月餘額 (千元)
    max_limit: Optional[int] = None      # 最高限額 (千元)


class EndorsementGuarantee(BaseModel):
    """背書保證資訊"""
    entity: str                              # 本公司/各子公司
    has_balance: bool                        # 是否有餘額
    monthly_change: Optional[int] = None     # 本月增減金額 (千元)
    accumulated_balance: Optional[int] = None # 累計餘額 (千元)
    max_limit: Optional[int] = None          # 最高額度 (千元)


class CrossCompanyGuarantee(BaseModel):
    """本公司與子公司間背書保證"""
    parent_to_subsidiary: Optional[int] = None  # 本公司對子公司累計餘額
    subsidiary_to_parent: Optional[int] = None  # 子公司對本公司累計餘額


class ChinaGuarantee(BaseModel):
    """對大陸地區背書保證"""
    entity: str
    has_balance: bool
    monthly_change: Optional[int] = None
    accumulated_balance: Optional[int] = None


class DisclosureResponse(BaseModel):
    """重大資訊揭露回應"""
    stock_id: str
    company_name: str
    year: int
    month: int
    
    # 資金貸放
    funds_lending: List[FundsLending] = []
    
    # 背書保證
    endorsement_guarantee: List[EndorsementGuarantee] = []
    
    # 本公司與子公司間背書保證
    cross_company: Optional[CrossCompanyGuarantee] = None
    
    # 對大陸地區背書保證
    china_guarantee: List[ChinaGuarantee] = []
