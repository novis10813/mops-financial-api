"""
Dividend Service - 股利分派服務

Fetches and parses dividend distribution data from MOPS.

MOPS AJAX:
- ajax_t05st09: 股利分派情形-經股東會確認 (年度股利、舊制)
- ajax_t05st09_2: 股利分派情形（含季度） (適用季配息公司如台積電)
"""
import logging
from typing import Optional, List
from decimal import Decimal

from app.schemas.dividend import DividendRecord, DividendSummary, DividendResponse
from app.utils.numerics import parse_financial_value
from app.services.mops_html_client import (
    get_mops_html_client,
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)





class DividendServiceError(Exception):
    """Dividend Service Error"""
    pass


class DividendService:
    """
    股利分派服務
    
    使用 ajax_t05st09_2 端點，支援季配息公司
    """
    
    # 使用 t05st09_2 支援季配息
    AJAX_ENDPOINT = "ajax_t05st09_2"
    
    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or get_mops_html_client()
    
    async def get_dividends(
        self,
        stock_id: str,
        year_start: int,  # 民國年
        year_end: Optional[int] = None,
        query_type: int = 2,  # 1=董事會決議年度, 2=股利所屬年度
    ) -> DividendResponse:
        """
        取得股利分派資料
        
        Args:
            stock_id: 股票代號
            year_start: 起始年度 (民國年)
            year_end: 結束年度 (預設同 year_start)
            query_type: 查詢類型 (1=董事會決議年度, 2=股利所屬年度)
        
        Returns:
            DividendResponse
        """
        if year_end is None:
            year_end = year_start
        
        params = {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "isnew": "false",      # 查詢歷史資料
            "co_id": stock_id,
            "date1": year_start,
            "date2": year_end,
            "qryType": str(query_type),
        }
        
        logger.info(f"Fetching dividend data: {stock_id} {year_start}-{year_end}")
        
        try:
            dfs = await self.client.fetch_html_table(
                self.AJAX_ENDPOINT,
                params,
                method="POST",
                encoding="utf-8",
            )
        except MOPSDataNotFoundError:
            raise DividendServiceError(f"No dividend data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise DividendServiceError(f"Failed to fetch dividend: {e.message}")
        
        # Parse dividend records
        company_name = self._extract_company_name(dfs, stock_id)
        records = self._parse_dividend_records(dfs, stock_id, company_name)
        
        logger.info(f"Parsed {len(records)} dividend records for {stock_id}")
        
        return DividendResponse(
            stock_id=stock_id,
            company_name=company_name,
            year_start=year_start,
            year_end=year_end,
            count=len(records),
            records=records,
        )
    
    async def get_annual_summary(
        self,
        stock_id: str,
        year: int,
    ) -> DividendSummary:
        """
        取得年度股利彙總
        
        自動合計季度股利
        """
        response = await self.get_dividends(stock_id, year, year)
        
        total_cash = sum(r.cash_dividend or 0 for r in response.records)
        total_stock = sum(r.stock_dividend or 0 for r in response.records)
        
        return DividendSummary(
            stock_id=stock_id,
            company_name=response.company_name,
            year=year,
            total_cash_dividend=round(total_cash, 2),
            total_stock_dividend=round(total_stock, 2),
            total_dividend=round(total_cash + total_stock, 2),
            quarterly_dividends=response.records,
        )
    
    def _extract_company_name(self, dfs: list, stock_id: str) -> str:
        """從表格中提取公司名稱"""
        for df in dfs:
            if df.shape[0] == 0:
                continue
            val = str(df.iloc[0, 0]) if df.shape[1] > 0 else ""
            if stock_id in val:
                # 格式通常是 "2330台灣積體電路製造股份有限公司"
                return val.replace(stock_id, "").strip()
        return ""
    
    def _parse_dividend_records(
        self,
        dfs: list,
        stock_id: str,
        company_name: str,
    ) -> List[DividendRecord]:
        """解析股利分派記錄"""
        records = []
        
        failure_count = 0

        for df in dfs:
            if df.shape[1] < 3 or df.shape[0] < 2:
                continue
            
            # 找到包含「股利所屬期間」的表格
            df_str = df.to_string()
            if "股利所屬期間" not in df_str and "現金股利" not in df_str:
                continue
            
            # 重設欄位名稱
            df.columns = range(len(df.columns))
            
            for idx, row in df.iterrows():
                try:
                    # 跳過標題行
                    first_col = str(row[0]).strip()
                    if "股利" in first_col or "期間" in first_col or first_col == "":
                        continue
                    
                    # 嘗試解析年度
                    year = self._extract_year(str(row[1]) if len(row) > 1 else "")
                    if year is None:
                        continue
                    
                    # 解析期間
                    period_str = str(row[1]) if len(row) > 1 else ""
                    quarter = self._extract_quarter(period_str)
                    
                    # Helper for float parsing
                    def _p_float(val):
                        d = parse_financial_value(val)
                        return float(d) if d is not None else None

                    # 解析現金股利
                    cash_dividend = _p_float(row[6]) if len(row) > 6 else None
                    
                    # 解析股票股利
                    stock_dividend = _p_float(row[7]) if len(row) > 7 else None
                    
                    # 董事會決議日
                    board_date = str(row[2]).strip() if len(row) > 2 else None
                    if board_date in ['nan', '', '-']:
                        board_date = None
                    
                    records.append(DividendRecord(
                        stock_id=stock_id,
                        company_name=company_name,
                        year=year,
                        quarter=quarter,
                        period_start=None,
                        period_end=None,
                        board_resolution_date=board_date,
                        cash_dividend=cash_dividend,
                        stock_dividend=stock_dividend,
                        total_dividend=(cash_dividend or 0) + (stock_dividend or 0),
                    ))
                    
                except Exception as e:
                    failure_count += 1
                    logger.debug(f"Failed to parse dividend row: {e}")
                    continue
        
        if failure_count > 0:
            logger.warning(f"Encountered {failure_count} errors while parsing dividend records for {stock_id}")

        return records
    
    def _extract_year(self, text: str) -> Optional[int]:
        """提取民國年"""
        import re
        match = re.search(r"(\d+)年", text)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_quarter(self, text: str) -> Optional[int]:
        """提取季度"""
        if "01/01" in text or "03/31" in text:
            return 1
        elif "04/01" in text or "06/30" in text:
            return 2
        elif "07/01" in text or "09/30" in text:
            return 3
        elif "10/01" in text or "12/31" in text:
            return 4
        return None
    



# Singleton instance
_dividend_service: Optional[DividendService] = None


def get_dividend_service() -> DividendService:
    """Get dividend service instance (singleton)"""
    global _dividend_service
    if _dividend_service is None:
        _dividend_service = DividendService()
    return _dividend_service
