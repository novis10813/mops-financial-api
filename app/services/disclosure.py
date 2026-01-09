"""
Disclosure Service - 重大資訊揭露服務

Fetches and parses disclosure data from MOPS including:
- 資金貸放 (Funds Lending)
- 背書保證 (Endorsement/Guarantee)

MOPS AJAX: ajax_t05st11
"""
import logging
from typing import Optional, List
from decimal import Decimal

from app.schemas.disclosure import (
    FundsLending,
    EndorsementGuarantee,
    CrossCompanyGuarantee,
    ChinaGuarantee,
    DisclosureResponse,
)
from app.utils.numerics import parse_financial_value

from app.services.mops_html_client import (
    get_mops_html_client,
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)





class DisclosureServiceError(Exception):
    """Disclosure Service Error"""
    pass


class DisclosureService:
    """
    重大資訊揭露服務
    
    MOPS AJAX: ajax_t05st11
    """
    
    AJAX_ENDPOINT = "ajax_t05st11"
    
    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or get_mops_html_client()
    
    async def get_disclosure(
        self,
        stock_id: str,
        year: int,  # 民國年
        month: int,
        market: str = "sii",
    ) -> DisclosureResponse:
        """
        取得重大資訊揭露（資金貸放 + 背書保證）
        
        Args:
            stock_id: 股票代號
            year: 民國年
            month: 月份 (1-12)
            market: 市場類型 (sii/otc)
        
        Returns:
            DisclosureResponse
        """
        params = {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "TYPEK": market,
            "year": year,
            "month": month,
            "co_id": stock_id,
        }
        
        logger.info(f"Fetching disclosure data: {stock_id} {year}/{month}")
        
        try:
            dfs = await self.client.fetch_html_table(
                self.AJAX_ENDPOINT,
                params,
                method="POST",
                encoding="utf-8",
            )
        except MOPSDataNotFoundError:
            raise DisclosureServiceError(f"No disclosure data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise DisclosureServiceError(f"Failed to fetch disclosure: {e.message}")
        
        # Parse data
        company_name = self._extract_company_name(dfs)
        funds_lending = self._parse_funds_lending(dfs)
        endorsement = self._parse_endorsement(dfs)
        cross_company = self._parse_cross_company(dfs)
        china_guarantee = self._parse_china_guarantee(dfs)
        
        logger.info(f"Parsed disclosure for {stock_id}: {len(funds_lending)} lending, {len(endorsement)} guarantee")
        
        return DisclosureResponse(
            stock_id=stock_id,
            company_name=company_name,
            year=year,
            month=month,
            funds_lending=funds_lending,
            endorsement_guarantee=endorsement,
            cross_company=cross_company,
            china_guarantee=china_guarantee,
        )
    
    def _extract_company_name(self, dfs: list) -> str:
        """從表格提取公司名稱"""
        for df in dfs:
            if df.shape[0] > 0:
                val = str(df.iloc[0, 0])
                if "公司" in val:
                    # 格式: "本資料由　(上市公司) 鴻海　公司提供"
                    import re
                    match = re.search(r"\)\s*(.+?)\s*公司", val)
                    if match:
                        return match.group(1)
        return ""
    
    def _parse_funds_lending(self, dfs: list) -> List[FundsLending]:
        """解析資金貸放表格"""
        results = []
        
        for df in dfs:
            df_str = df.to_string()
            if "資金貸放餘額" not in df_str:
                continue
            
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "資金貸放餘額" not in first_col:
                        continue
                    
                    entity = "本公司" if "本公司" in first_col else "子公司"
                    has_balance = "有" in first_col
                    
                    results.append(FundsLending(
                        entity=entity,
                        has_balance=has_balance,
                        current_month=self._parse_int(row.iloc[1]) if len(row) > 1 else None,
                        previous_month=self._parse_int(row.iloc[2]) if len(row) > 2 else None,
                        max_limit=self._parse_int(row.iloc[3]) if len(row) > 3 else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse funds lending row: {e}")
        
        return results
    
    def _parse_endorsement(self, dfs: list) -> List[EndorsementGuarantee]:
        """解析背書保證表格"""
        results = []
        
        for df in dfs:
            df_str = df.to_string()
            if "背書保證資訊" not in df_str or "大陸" in df_str or "子公司間" in df_str:
                continue
            
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "背書保證資訊" not in first_col:
                        continue
                    
                    entity = "本公司" if "本公司 " in first_col else "子公司"
                    has_balance = "有" in first_col
                    
                    results.append(EndorsementGuarantee(
                        entity=entity,
                        has_balance=has_balance,
                        monthly_change=self._parse_int(row.iloc[1]) if len(row) > 1 else None,
                        accumulated_balance=self._parse_int(row.iloc[2]) if len(row) > 2 else None,
                        max_limit=self._parse_int(row.iloc[3]) if len(row) > 3 else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse endorsement row: {e}")
        
        return results
    
    def _parse_cross_company(self, dfs: list) -> Optional[CrossCompanyGuarantee]:
        """解析本公司與子公司間背書保證"""
        for df in dfs:
            df_str = df.to_string()
            if "本公司與子公司間" not in df_str:
                continue
            
            p_to_s = None
            s_to_p = None
            
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0])
                if "本公司對子公司" in first_col:
                    p_to_s = self._parse_int(row.iloc[1]) if len(row) > 1 else None
                elif "子公司對本公司" in first_col:
                    s_to_p = self._parse_int(row.iloc[1]) if len(row) > 1 else None
            
            if p_to_s is not None or s_to_p is not None:
                return CrossCompanyGuarantee(
                    parent_to_subsidiary=p_to_s,
                    subsidiary_to_parent=s_to_p,
                )
        
        return None
    
    def _parse_china_guarantee(self, dfs: list) -> List[ChinaGuarantee]:
        """解析對大陸地區背書保證"""
        results = []
        
        for df in dfs:
            df_str = df.to_string()
            if "對大陸地區" not in df_str:
                continue
            
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "大陸地區" not in first_col:
                        continue
                    
                    entity = "本公司" if "本公司" in first_col else "子公司"
                    has_balance = "有" in first_col
                    
                    results.append(ChinaGuarantee(
                        entity=entity,
                        has_balance=has_balance,
                        monthly_change=self._parse_int(row.iloc[1]) if len(row) > 1 else None,
                        accumulated_balance=self._parse_int(row.iloc[2]) if len(row) > 2 else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse china guarantee row: {e}")
        
        return results
    
    def _parse_int(self, value) -> Optional[int]:
        """Parse integer from string using centralized parser"""
        d = parse_financial_value(value)
        return int(d) if d is not None else None


# Singleton instance
_disclosure_service: Optional[DisclosureService] = None


def get_disclosure_service() -> DisclosureService:
    """Get disclosure service instance (singleton)"""
    global _disclosure_service
    if _disclosure_service is None:
        _disclosure_service = DisclosureService()
    return _disclosure_service
