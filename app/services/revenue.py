"""
Revenue Service - 月營收服務

Fetches and parses monthly revenue data from MOPS.

URL Pattern:
https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html

Note: year uses ROC year (民國年), consistent with other endpoints.
"""
import logging
from typing import Optional, List
from datetime import date
from decimal import Decimal

from app.schemas.revenue import MonthlyRevenue
from app.utils.numerics import parse_financial_value
from app.services.mops_html_client import (
    get_mops_html_client,
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)





class RevenueServiceError(Exception):
    """Revenue Service Error"""
    pass


class RevenueService:
    """
    月營收服務
    
    URL Pattern:
    https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html
    
    Markets:
    - sii: 上市
    - otc: 上櫃
    - rotc: 興櫃
    - pub: 公開發行
    """
    
    MARKET_TYPES = {
        "sii": "上市",
        "otc": "上櫃",
        "rotc": "興櫃",
        "pub": "公開發行",
    }
    
    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or get_mops_html_client()
    
    async def get_market_revenue(
        self,
        year: int,  # 民國年
        month: int,
        market: str = "sii",
        company_type: int = 0,  # 0=國內, 1=國外
    ) -> List[MonthlyRevenue]:
        """
        取得全市場月營收資料
        
        Args:
            year: 民國年 (e.g., 113)
            month: 月份 (1-12)
            market: 市場類型 (sii/otc/rotc/pub)
            company_type: 公司類型 (0=國內, 1=國外)
        
        Returns:
            List of MonthlyRevenue
        """
        if market not in self.MARKET_TYPES:
            raise RevenueServiceError(f"Invalid market: {market}")
        
        url = self.client.REVENUE_URL_PATTERN.format(
            market=market,
            year=year,
            month=month,
            company_type=company_type,
        )
        
        logger.info(f"Fetching revenue data: {year}/{month} from {market}")
        
        try:
            dfs = await self.client.fetch_static_html(url, encoding="big5")
        except MOPSDataNotFoundError:
            raise RevenueServiceError(f"No revenue data for {year}/{month}")
        except MOPSHTMLClientError as e:
            raise RevenueServiceError(f"Failed to fetch revenue: {e.message}")
        
        # Parse all tables and extract revenue data
        revenues = self._parse_revenue_tables(dfs, year, month)
        
        logger.info(f"Parsed {len(revenues)} companies from {market} {year}/{month}")
        return revenues
    
    async def get_single_revenue(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> Optional[MonthlyRevenue]:
        """
        取得單一公司月營收
        
        Args:
            stock_id: 股票代號
            year: 民國年
            month: 月份
            market: 市場類型
        
        Returns:
            MonthlyRevenue or None if not found
        """
        revenues = await self.get_market_revenue(year, month, market)
        
        for rev in revenues:
            if rev.stock_id == stock_id:
                return rev
        
        return None
    
    def _parse_revenue_tables(
        self,
        dfs: list,
        year: int,
        month: int,
    ) -> List[MonthlyRevenue]:
        """
        解析 MOPS 月營收 HTML 表格
        
        MOPS 回傳多個表格，每個產業一個表格。
        每個表格的結構：
        - 第一列是標題行（公司代號, 公司名稱, 當月營收, ...）
        - 最後一列通常是「合計」
        """
        revenues: List[MonthlyRevenue] = []
        
        for i, df in enumerate(dfs):
            # Skip tables that are too small or are headers
            if df.shape[0] < 2 or df.shape[1] < 5:
                continue
            
            # Try to parse this table
            table_revenues = self._parse_single_table(df, year, month)
            revenues.extend(table_revenues)
        
        return revenues
    
    def _parse_single_table(
        self,
        df,
        year: int,
        month: int,
    ) -> List[MonthlyRevenue]:
        """解析單一產業表格"""
        revenues = []
        
        # The table structure varies, but typically:
        # 公司代號 | 公司名稱 | 當月營收 | 上月營收 | 去年當月營收 | 上月比較增減(%) | 去年同月增減(%) | 當月累計營收 | 去年累計營收 | 前期比較增減(%) | 備註
        
        failure_count = 0
        
        # Reset column names to numeric index for easier access
        df.columns = range(len(df.columns))
        
        for idx, row in df.iterrows():
            try:
                # Get stock_id from first column
                stock_id = str(row[0]).strip()
                
                # Skip if not a valid stock code (4-6 digits or alphanumeric)
                if not stock_id or len(stock_id) < 4 or stock_id in ['合計', '公司代號', '公司', '合計:']:
                    continue
                
                # Check if stock_id starts with a digit
                if not stock_id[0].isdigit():
                    continue
                
                # Parse company name
                company_name = str(row[1]).strip() if len(row) > 1 else ""
                
                # Helper to parse int/float from Decimal
                def _p_int(val):
                    d = parse_financial_value(val)
                    return int(d) if d is not None else None

                def _p_float(val):
                    d = parse_financial_value(val)
                    return float(d) if d is not None else None

                # Parse numeric fields with error handling
                # columns: 2=revenue, 3=last_month, 4=last_year, 5=mom, 6=yoy, 7=acc, 8=acc_last, 9=acc_yoy
                revenue = _p_int(row[2]) if len(row) > 2 else None
                revenue_last_month = _p_int(row[3]) if len(row) > 3 else None
                revenue_last_year = _p_int(row[4]) if len(row) > 4 else None
                mom_change = _p_float(row[5]) if len(row) > 5 else None
                yoy_change = _p_float(row[6]) if len(row) > 6 else None
                accumulated_revenue = _p_int(row[7]) if len(row) > 7 else None
                accumulated_last_year = _p_int(row[8]) if len(row) > 8 else None
                accumulated_yoy_change = _p_float(row[9]) if len(row) > 9 else None
                
                comment = str(row[10]).strip() if len(row) > 10 and str(row[10]).strip() not in ['-', 'nan', '', 'None'] else None
                
                revenues.append(MonthlyRevenue(
                    stock_id=stock_id,
                    company_name=company_name,
                    year=year,
                    month=month,
                    revenue=revenue,
                    revenue_last_month=revenue_last_month,
                    revenue_last_year=revenue_last_year,
                    mom_change=mom_change,
                    yoy_change=yoy_change,
                    accumulated_revenue=accumulated_revenue,
                    accumulated_last_year=accumulated_last_year,
                    accumulated_yoy_change=accumulated_yoy_change,
                    comment=comment if comment and comment != 'nan' else None,
                ))
                
            except Exception as e:
                # Log unexpected errors as warning/error instead of debug
                failure_count += 1
                if failure_count <= 5: # Limit log noise
                    logger.warning(f"Error parsing revenue row {idx} for {year}/{month}: {e}")
                elif failure_count == 6:
                    logger.warning(f"Too many parsing errors in {year}/{month}, suppressing further logs.")
                continue
        
        if failure_count > 0:
            logger.info(f"Finished parsing table with {failure_count} failed rows.")

        return revenues
    



# Singleton instance
_revenue_service: Optional[RevenueService] = None


def get_revenue_service() -> RevenueService:
    """Get revenue service instance (singleton)"""
    global _revenue_service
    if _revenue_service is None:
        _revenue_service = RevenueService()
    return _revenue_service
