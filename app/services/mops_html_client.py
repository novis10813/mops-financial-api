"""
MOPS (公開資訊觀測站) HTML Client
Fetches and parses HTML tables from TWSE MOPS

This client is specifically for HTML table data (revenue, pledging, etc.)
For XBRL financial report downloads, use MOPSXBRLClient instead.

Key Features:
- Rate limiting to avoid IP ban
- Big5/UTF-8 encoding handling
- pandas.read_html() for table parsing
"""
import asyncio
import logging
import time
from io import StringIO
from typing import Optional

import httpx
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class MOPSHTMLClientError(Exception):
    """MOPS HTML Client Error (base class)"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MOPSRateLimitError(MOPSHTMLClientError):
    """Raised when MOPS rate limits the request"""
    pass


class MOPSDataNotFoundError(MOPSHTMLClientError):
    """Raised when requested data doesn't exist"""
    pass


class MOPSParsingError(MOPSHTMLClientError):
    """Raised when HTML parsing fails"""
    pass


class MOPSHTMLClient:
    """
    MOPS 公開資訊觀測站 HTML 客戶端
    
    專門用於爬取 HTML 表格資料（月營收、質押、背書保證等）
    
    Features:
    - Rate limiting (預設 1 req/sec)
    - Big5/UTF-8 編碼處理
    - 使用 pandas.read_html() 解析表格
    """
    
    # Note: mopsov.twse.com.tw is the correct data server
    # mops.twse.com.tw redirects but may have security restrictions
    MOPS_BASE = "https://mopsov.twse.com.tw"
    MOPS_AJAX_BASE = f"{MOPS_BASE}/mops/web"
    
    # URL pattern for static monthly revenue HTML
    REVENUE_URL_PATTERN = f"{MOPS_BASE}/nas/t21/{{market}}/t21sc03_{{year}}_{{month}}_{{company_type}}.html"
    
    # Common headers to avoid being blocked
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3):
        """
        Initialize MOPS HTML Client
        
        Args:
            rate_limit: Minimum seconds between requests (default: 1.0)
            max_retries: Maximum retry attempts for failed requests
        """
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self._last_request_time: float = 0
        self.timeout = getattr(settings, 'request_timeout', 30.0)
    
    async def _rate_limit_wait(self):
        """Enforce rate limiting between requests"""
        now = time.time()
        wait_time = self.rate_limit - (now - self._last_request_time)
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()
    
    def _get_headers(self, referer: Optional[str] = None) -> dict:
        """Get request headers with optional referer"""
        headers = self.DEFAULT_HEADERS.copy()
        headers["Referer"] = referer or self.MOPS_BASE
        return headers
    
    async def fetch_html_table(
        self,
        endpoint: str,
        params: dict,
        method: str = "POST",
        encoding: str = "utf-8",
    ) -> list[pd.DataFrame]:
        """
        從 MOPS AJAX 端點抓取 HTML 表格並轉為 DataFrame
        
        Args:
            endpoint: MOPS 端點名稱 (e.g., "ajax_t21sb01")
            params: 請求參數 (form data for POST, query params for GET)
            method: HTTP 方法 ("POST" or "GET")
            encoding: 回應編碼 ("utf-8" or "big5")
        
        Returns:
            解析後的 DataFrame 列表
        
        Raises:
            MOPSHTMLClientError: 請求或解析失敗
        """
        await self._rate_limit_wait()
        
        url = f"{self.MOPS_AJAX_BASE}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    verify=False,
                    follow_redirects=True,
                ) as client:
                    if method.upper() == "POST":
                        resp = await client.post(
                            url, 
                            data=params, 
                            headers=self._get_headers(url)
                        )
                    else:
                        resp = await client.get(
                            url, 
                            params=params, 
                            headers=self._get_headers(url)
                        )
                    
                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", 
                            resp.status_code
                        )
                    
                    # Set encoding and get text
                    resp.encoding = encoding
                    html_content = resp.text
                    
                    # Check for "查無資料" (no data found)
                    if "查無資料" in html_content or "查無符合資料" in html_content:
                        raise MOPSDataNotFoundError("No data found for the query")
                    
                    # Parse HTML tables
                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from {endpoint}")
                        return dfs
                    except ValueError as e:
                        # pd.read_html raises ValueError when no tables found
                        raise MOPSParsingError(f"No tables found in response: {e}")
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries} for {endpoint}")
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                await asyncio.sleep(1 * (attempt + 1))
                
            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")
            
            except (MOPSDataNotFoundError, MOPSParsingError):
                # Don't retry these errors
                raise
        
        raise MOPSHTMLClientError(f"Failed to fetch data from {endpoint}")
    
    async def fetch_static_html(
        self,
        url: str,
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        抓取靜態 HTML 頁面 (如月營收彙總表)
        
        Args:
            url: 完整的 URL
            encoding: 回應編碼 (通常是 "big5" for 舊頁面)
        
        Returns:
            解析後的 DataFrame 列表
        
        Raises:
            MOPSHTMLClientError: 請求或解析失敗
        """
        await self._rate_limit_wait()
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    verify=False,
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(url, headers=self._get_headers())
                    
                    if resp.status_code == 404:
                        raise MOPSDataNotFoundError(f"Page not found: {url}")
                    
                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", 
                            resp.status_code
                        )
                    
                    # Set encoding and get text
                    resp.encoding = encoding
                    html_content = resp.text
                    
                    # Parse HTML tables
                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from static HTML")
                        return dfs
                    except ValueError as e:
                        raise MOPSParsingError(f"No tables found in response: {e}")
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                await asyncio.sleep(1 * (attempt + 1))
                
            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")
            
            except (MOPSDataNotFoundError, MOPSParsingError):
                raise
        
        raise MOPSHTMLClientError(f"Failed to fetch static HTML from {url}")


# Singleton instance
_mops_html_client: Optional[MOPSHTMLClient] = None


def get_mops_html_client() -> MOPSHTMLClient:
    """Get MOPS HTML client instance (singleton)"""
    global _mops_html_client
    if _mops_html_client is None:
        _mops_html_client = MOPSHTMLClient()
    return _mops_html_client
