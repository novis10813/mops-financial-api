"""
MOPS (公開資訊觀測站) XBRL Client
Downloads XBRL/iXBRL financial report files from TWSE MOPS

This client is specifically for XBRL format downloads.
For HTML table crawling, use MOPSHTMLClient instead.

Download endpoint:
/server-java/FileDownLoad?functionName=t164sb01&step=9&co_id={stock_id}&year={year}&season={quarter}&report_id=C
"""
import asyncio
import io
import logging
import zipfile
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MOPSXBRLClientError(Exception):
    """MOPS XBRL Client Error"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Backward compatibility alias
MOPSClientError = MOPSXBRLClientError


class MOPSXBRLClient:
    """
    MOPS 公開資訊觀測站 XBRL 客戶端
    
    專門用於下載 iXBRL 財報檔案
    """
    
    MOPS_BASE = "https://mopsov.twse.com.tw"
    DOWNLOAD_URL = "{base}/server-java/FileDownLoad?functionName=t164sb01&step=9&co_id={stock_id}&year={year}&season={quarter}&report_id={report_id}"
    
    def __init__(self):
        self.timeout = settings.request_timeout
        self.max_retries = settings.max_retries
    
    async def download_xbrl(
        self, 
        stock_id: str, 
        year: int, 
        quarter: int,
        report_type: str = "C",  # C=合併, A=個別
    ) -> bytes:
        """
        從 MOPS 下載 iXBRL 檔案
        
        Args:
            stock_id: 股票代號 (e.g., "2330")
            year: 民國年 (e.g., 113)
            quarter: 季度 (1-4)
            report_type: 報表類型 (C=合併報表, A=個別報表)
        
        Returns:
            iXBRL 檔案的 bytes
        """
        # 轉換民國年為西元年
        western_year = year + 1911
        
        download_url = self.DOWNLOAD_URL.format(
            base=self.MOPS_BASE,
            stock_id=stock_id,
            year=western_year,
            quarter=quarter,
            report_id=report_type
        )
        
        logger.info(f"Downloading from MOPS: {stock_id} {year}Q{quarter}")
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, 
                    verify=False,
                    follow_redirects=True
                ) as client:
                    resp = await client.get(download_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": f"{self.MOPS_BASE}/mops/web/t203sb01",
                    })
                    
                    if resp.status_code == 200:
                        content = resp.content
                        
                        if self.is_ixbrl(content):
                            logger.info(f"Downloaded iXBRL ({len(content):,} bytes)")
                            return content
                        
                        if content[:2] == b"PK":
                            logger.info(f"Downloaded ZIP ({len(content):,} bytes)")
                            return content
                        
                        raise MOPSXBRLClientError("MOPS returned invalid content")
                    else:
                        raise MOPSXBRLClientError(f"HTTP {resp.status_code}", resp.status_code)
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSXBRLClientError("Download timeout")
                await asyncio.sleep(1 * (attempt + 1))
                
            except httpx.HTTPError as e:
                raise MOPSXBRLClientError(f"HTTP error: {e}")
        
        raise MOPSXBRLClientError(f"Failed to download XBRL for {stock_id} {year}Q{quarter}")
    
    def extract_zip(self, zip_content: bytes) -> dict[str, bytes]:
        """解壓縮 XBRL ZIP 檔案"""
        files = {}
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            for name in zf.namelist():
                files[name] = zf.read(name)
        return files
    
    def is_ixbrl(self, content: bytes) -> bool:
        """檢查內容是否為 iXBRL 格式"""
        return b"ix:nonFraction" in content or b"ix:nonNumeric" in content


_mops_xbrl_client: Optional[MOPSXBRLClient] = None


def get_mops_xbrl_client() -> MOPSXBRLClient:
    """Get MOPS XBRL client instance (singleton)"""
    global _mops_xbrl_client
    if _mops_xbrl_client is None:
        _mops_xbrl_client = MOPSXBRLClient()
    return _mops_xbrl_client


# Backward compatibility alias
get_mops_client = get_mops_xbrl_client
