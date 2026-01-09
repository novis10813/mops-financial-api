"""
Insiders Service - 董監事質押服務

Fetches and parses share pledging data from MOPS.

MOPS AJAX:
POST https://mopsov.twse.com.tw/mops/web/ajax_stapap1
"""
import logging
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel

from app.services.mops_html_client import (
    get_mops_html_client,
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)


class SharePledging(BaseModel):
    """董監事質押資料 - 個人明細"""
    stock_id: str                    # 股票代號
    company_name: str                # 公司名稱
    year: int                        # 民國年
    month: int                       # 月份
    title: str                       # 職稱 (董事長/獨立董事/副總經理等)
    relationship: str                # 本人/配偶
    name: str                        # 姓名
    shares_at_election: Optional[int] = None  # 選任時持股
    current_shares: Optional[int] = None      # 目前持股
    pledged_shares: Optional[int] = None      # 設質股數
    pledge_ratio: Optional[float] = None      # 設質比例 (%)


class PledgingSummary(BaseModel):
    """董監事質押資料 - 彙總"""
    stock_id: str
    company_name: str
    year: int
    month: int
    
    # 非獨立董事
    non_independent_director_shares: Optional[int] = None
    non_independent_director_pledged: Optional[int] = None
    non_independent_director_ratio: Optional[float] = None
    
    # 獨立董事
    independent_director_shares: Optional[int] = None
    independent_director_pledged: Optional[int] = None
    independent_director_ratio: Optional[float] = None
    
    # 全體董監
    total_shares: Optional[int] = None
    total_pledged: Optional[int] = None
    total_pledge_ratio: Optional[float] = None


class PledgingResponse(BaseModel):
    """質押資料回應"""
    stock_id: str
    company_name: str
    year: int
    month: int
    summary: Optional[PledgingSummary] = None
    details: List[SharePledging] = []


class InsidersServiceError(Exception):
    """Insiders Service Error"""
    pass


class InsidersService:
    """
    董監事質押服務
    
    MOPS AJAX: POST https://mopsov.twse.com.tw/mops/web/ajax_stapap1
    """
    
    AJAX_ENDPOINT = "ajax_stapap1"
    
    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or get_mops_html_client()
    
    async def get_share_pledging(
        self,
        stock_id: str,
        year: int,  # 民國年
        month: int,
        market: str = "sii",
    ) -> PledgingResponse:
        """
        取得單一公司的董監事質押資料
        
        Args:
            stock_id: 股票代號
            year: 民國年 (e.g., 113)
            month: 月份 (1-12)
            market: 市場類型 (sii/otc)
        
        Returns:
            PledgingResponse 包含明細和彙總
        """
        params = {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "TYPEK": market,
            "year": year,
            "month": str(month).zfill(2),
            "co_id": stock_id,
        }
        
        logger.info(f"Fetching pledging data: {stock_id} {year}/{month}")
        
        try:
            dfs = await self.client.fetch_html_table(
                self.AJAX_ENDPOINT,
                params,
                method="POST",
                encoding="utf-8",
            )
        except MOPSDataNotFoundError:
            raise InsidersServiceError(f"No pledging data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise InsidersServiceError(f"Failed to fetch pledging: {e.message}")
        
        # Parse tables
        company_name = self._extract_company_name(dfs, stock_id)
        details = self._parse_pledging_details(dfs, stock_id, company_name, year, month)
        summary = self._parse_pledging_summary(dfs, stock_id, company_name, year, month)
        
        logger.info(f"Parsed {len(details)} pledging records for {stock_id}")
        
        return PledgingResponse(
            stock_id=stock_id,
            company_name=company_name,
            year=year,
            month=month,
            summary=summary,
            details=details,
        )
    
    def _extract_company_name(self, dfs: list, stock_id: str) -> str:
        """從表格中提取公司名稱"""
        if dfs and len(dfs) > 0:
            # 第一個表格通常包含公司代號和名稱
            first_table = dfs[0]
            if len(first_table) > 0:
                val = str(first_table.iloc[0, 0])
                # 格式通常是 "2330台灣積體電路製造股份有限公司"
                if val.startswith(stock_id):
                    return val[len(stock_id):]
        return ""
    
    def _parse_pledging_details(
        self,
        dfs: list,
        stock_id: str,
        company_name: str,
        year: int,
        month: int,
    ) -> List[SharePledging]:
        """解析質押明細表格"""
        details = []
        
        # 明細資料通常在第三個表格 (index 2 或 3)
        for df in dfs:
            if df.shape[1] < 5:
                continue
            
            # 找到包含「職稱」和「姓名」的表格
            first_col = str(df.iloc[0, 0]) if len(df) > 0 else ""
            if "職稱" not in first_col and df.shape[0] < 3:
                continue
            
            # 重設欄位名稱
            df.columns = range(len(df.columns))
            
            for idx, row in df.iterrows():
                try:
                    title = str(row[0]).strip()
                    
                    # 跳過標題行
                    if title == "職稱" or "持股" in title:
                        continue
                    
                    # 拆分職稱和關係 (如 "董事長本人" -> title="董事長", relationship="本人")
                    relationship = "本人"
                    if "本人" in title:
                        title = title.replace("本人", "")
                    elif "配偶" in title:
                        relationship = "配偶"
                        title = title.replace("配偶", "")
                    
                    name = str(row[1]).strip() if len(row) > 1 else ""
                    if not name or name == "姓名":
                        continue
                    
                    shares_at_election = self._parse_int(row[2]) if len(row) > 2 else None
                    current_shares = self._parse_int(row[3]) if len(row) > 3 else None
                    pledged_shares = self._parse_int(row[4]) if len(row) > 4 else None
                    pledge_ratio = self._parse_percentage(row[5]) if len(row) > 5 else None
                    
                    details.append(SharePledging(
                        stock_id=stock_id,
                        company_name=company_name,
                        year=year,
                        month=month,
                        title=title,
                        relationship=relationship,
                        name=name,
                        shares_at_election=shares_at_election,
                        current_shares=current_shares,
                        pledged_shares=pledged_shares,
                        pledge_ratio=pledge_ratio,
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse pledging row: {e}")
                    continue
        
        return details
    
    def _parse_pledging_summary(
        self,
        dfs: list,
        stock_id: str,
        company_name: str,
        year: int,
        month: int,
    ) -> Optional[PledgingSummary]:
        """解析質押彙總表格"""
        # 彙總表格通常是倒數第二個
        for df in dfs:
            # 找到包含「全體董監持股合計」的表格
            df_str = df.to_string()
            if "全體董監持股合計" not in df_str:
                continue
            
            summary = PledgingSummary(
                stock_id=stock_id,
                company_name=company_name,
                year=year,
                month=month,
            )
            
            for idx, row in df.iterrows():
                row_str = str(row[0])
                
                if "非獨立董事持股合計" in row_str:
                    summary.non_independent_director_shares = self._parse_int(row[1])
                elif "非獨立董事持股設質合計" in row_str or row_str == "非獨立董事持股設質合計":
                    summary.non_independent_director_pledged = self._parse_int(row[1])
                elif "非獨立董事持股設質比例" in row_str:
                    summary.non_independent_director_ratio = self._parse_percentage(row[1])
                elif "獨立董事持股合計" in row_str:
                    summary.independent_director_shares = self._parse_int(row[1])
                elif "獨立董事持股設質合計" in row_str:
                    summary.independent_director_pledged = self._parse_int(row[1])
                elif "獨立董事持股設質比例" in row_str:
                    summary.independent_director_ratio = self._parse_percentage(row[1])
                elif "全體董監持股合計" in row_str:
                    summary.total_shares = self._parse_int(row[1])
                elif "全體董監持股設質合計" in row_str or row_str == "全體董監持股設質合計":
                    summary.total_pledged = self._parse_int(row[1])
                elif "全體董監持股設質比例" in row_str:
                    summary.total_pledge_ratio = self._parse_percentage(row[1])
            
            return summary
        
        return None
    
    def _parse_int(self, value) -> Optional[int]:
        """Parse integer from string"""
        if value is None:
            return None
        
        str_val = str(value).strip()
        if str_val in ['', '-', 'nan', 'NaN', '不適用']:
            return None
        
        try:
            clean_val = str_val.replace(',', '').replace(' ', '')
            return int(float(clean_val))
        except (ValueError, TypeError):
            return None
    
    def _parse_percentage(self, value) -> Optional[float]:
        """Parse percentage string (e.g., "0.09%")"""
        if value is None:
            return None
        
        str_val = str(value).strip()
        if str_val in ['', '-', 'nan', 'NaN']:
            return None
        
        try:
            # Remove % sign
            clean_val = str_val.replace('%', '').replace(',', '').strip()
            return round(float(clean_val), 2)
        except (ValueError, TypeError):
            return None


# Singleton instance
_insiders_service: Optional[InsidersService] = None


def get_insiders_service() -> InsidersService:
    """Get insiders service instance (singleton)"""
    global _insiders_service
    if _insiders_service is None:
        _insiders_service = InsidersService()
    return _insiders_service
