"""
Taxonomy Manager

Automatically downloads and manages Taiwan IFRS/GAAP taxonomies from MOPS.
Handles:
- Checking for missing or new taxonomies
- Downloading and extracting taxonomy ZIPs
- Generating schema mappings for Arelle

Usage:
    from app.services.taxonomy_manager import TaxonomyManager
    
    manager = TaxonomyManager()
    await manager.ensure_taxonomies()  # Download missing taxonomies
    mappings = manager.get_schema_mappings()  # Get dynamic mappings
"""

import asyncio
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# MOPS taxonomy download page
MOPS_TAXONOMY_PAGE = "https://mopsov.twse.com.tw/mops/web/t203sb03"
MOPS_TAXONOMY_BASE_URL = "https://mopsov.twse.com.tw/nas/taxonomy/"

# Default taxonomy directory
DEFAULT_TAXONOMY_DIR = Path(__file__).parent.parent.parent / "taxonomy"


@dataclass
class TaxonomyInfo:
    """Information about a taxonomy package"""
    filename: str
    description: str
    publish_date: str
    taxonomy_type: str  # "tifrs" or "tw-gaap"
    start_year: int
    start_quarter: int
    end_year: Optional[int]
    end_quarter: Optional[int]
    is_ongoing: bool  # True for "2020年第2季起" format


class TaxonomyManager:
    """
    Manages Taiwan IFRS/GAAP taxonomies
    
    Responsibilities:
    - Scrape MOPS website for available taxonomies
    - Download and extract missing taxonomies
    - Generate schema mappings for Arelle
    - Determine which taxonomy to use for a given year/quarter
    """
    
    def __init__(self, taxonomy_dir: Optional[Path] = None):
        self.taxonomy_dir = taxonomy_dir or DEFAULT_TAXONOMY_DIR
        self.taxonomy_dir.mkdir(parents=True, exist_ok=True)
        self._taxonomies: List[TaxonomyInfo] = []
        self._schema_mappings: Dict[str, str] = {}
    
    async def ensure_taxonomies(self, force_refresh: bool = False) -> List[str]:
        """
        Ensure all taxonomies are downloaded and extracted
        
        Args:
            force_refresh: If True, re-scrape MOPS even if taxonomies exist
            
        Returns:
            List of newly downloaded taxonomy filenames
        """
        # Scrape MOPS for available taxonomies
        await self._scrape_taxonomy_list()
        
        downloaded = []
        for taxonomy in self._taxonomies:
            zip_path = self.taxonomy_dir / taxonomy.filename
            extract_dir = self.taxonomy_dir / taxonomy.filename.replace('.zip', '')
            
            # Download if ZIP doesn't exist
            if not zip_path.exists():
                logger.info(f"Downloading taxonomy: {taxonomy.filename}")
                await self._download_taxonomy(taxonomy.filename)
                downloaded.append(taxonomy.filename)
            
            # Extract if directory doesn't exist
            if not extract_dir.exists() and zip_path.exists():
                logger.info(f"Extracting taxonomy: {taxonomy.filename}")
                self._extract_taxonomy(zip_path, extract_dir)
        
        # Generate schema mappings
        self._generate_schema_mappings()
        
        return downloaded
    
    async def _scrape_taxonomy_list(self) -> None:
        """Scrape MOPS website for available taxonomy packages"""
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    MOPS_TAXONOMY_PAGE,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30.0
                )
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            self._taxonomies = []
            
            # Find the main content - look for taxonomy filenames
            text = soup.get_text()
            
            # Parse using regex patterns
            # Pattern 1: "2020年第2季起財報適用" (ongoing)
            # Pattern 2: "2019年第1季至2020年第1財報適用" (range)
            # Pattern 3: "2011年第3季財報適用" (single quarter)
            
            patterns = [
                # Ongoing: 2020年第2季起
                (r'(\d{4})年第(\d)季起財報適用\s*(tifrs-\d+\.zip|tw-gaap-[\d-]+\.zip)', 'ongoing'),
                # Range: 2019年第1季至2020年第1季
                (r'(\d{4})年第(\d)季至(\d{4})年第(\d)季?財報適用\s*(tifrs-\d+\.zip|tw-gaap-[\d-]+\.zip)', 'range'),
                # Single: 2011年第3季
                (r'(\d{4})年第(\d)季財報適用\s*(tifrs-\d+\.zip|tw-gaap-[\d-]+\.zip)', 'single'),
            ]
            
            for pattern, pattern_type in patterns:
                for match in re.finditer(pattern, text):
                    if pattern_type == 'ongoing':
                        start_year, start_q, filename = match.groups()
                        taxonomy = TaxonomyInfo(
                            filename=filename,
                            description=f"{start_year}年第{start_q}季起財報適用",
                            publish_date="",
                            taxonomy_type="tifrs" if filename.startswith("tifrs") else "tw-gaap",
                            start_year=int(start_year),
                            start_quarter=int(start_q),
                            end_year=None,
                            end_quarter=None,
                            is_ongoing=True
                        )
                    elif pattern_type == 'range':
                        start_year, start_q, end_year, end_q, filename = match.groups()
                        taxonomy = TaxonomyInfo(
                            filename=filename,
                            description=f"{start_year}年第{start_q}季至{end_year}年第{end_q}季財報適用",
                            publish_date="",
                            taxonomy_type="tifrs" if filename.startswith("tifrs") else "tw-gaap",
                            start_year=int(start_year),
                            start_quarter=int(start_q),
                            end_year=int(end_year),
                            end_quarter=int(end_q) if end_q else 4,
                            is_ongoing=False
                        )
                    else:  # single
                        year, quarter, filename = match.groups()
                        taxonomy = TaxonomyInfo(
                            filename=filename,
                            description=f"{year}年第{quarter}季財報適用",
                            publish_date="",
                            taxonomy_type="tifrs" if filename.startswith("tifrs") else "tw-gaap",
                            start_year=int(year),
                            start_quarter=int(quarter),
                            end_year=int(year),
                            end_quarter=int(quarter),
                            is_ongoing=False
                        )
                    
                    # Avoid duplicates
                    if not any(t.filename == taxonomy.filename for t in self._taxonomies):
                        self._taxonomies.append(taxonomy)
            
            logger.info(f"Found {len(self._taxonomies)} taxonomies from MOPS")
            
        except Exception as e:
            logger.error(f"Failed to scrape MOPS taxonomy list: {e}")
            # Fallback to known taxonomies
            self._use_fallback_list()
    
    def _use_fallback_list(self) -> None:
        """Use hardcoded fallback list if scraping fails"""
        fallback = [
            ("tifrs-20200630.zip", 2020, 2, None, None, True),
            ("tifrs-20190331.zip", 2019, 1, 2020, 1, False),
            ("tifrs-20180930.zip", 2018, 3, 2018, 4, False),
            ("tifrs-20180331.zip", 2018, 1, 2018, 2, False),
            ("tifrs-20170331.zip", 2017, 1, 2017, 4, False),
            ("tifrs-20150331.zip", 2015, 1, 2016, 4, False),
            ("tifrs-20140331.zip", 2014, 1, 2014, 4, False),
            ("tifrs-20130331.zip", 2013, 1, 2013, 4, False),
        ]
        
        self._taxonomies = [
            TaxonomyInfo(
                filename=f,
                description="",
                publish_date="",
                taxonomy_type="tifrs",
                start_year=sy, start_quarter=sq,
                end_year=ey, end_quarter=eq,
                is_ongoing=ongoing
            )
            for f, sy, sq, ey, eq, ongoing in fallback
        ]
    
    async def _download_taxonomy(self, filename: str) -> None:
        """Download a taxonomy ZIP file from MOPS"""
        url = f"{MOPS_TAXONOMY_BASE_URL}{filename}"
        zip_path = self.taxonomy_dir / filename
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded {filename} ({len(response.content) / 1024:.1f} KB)")
            
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            raise
    
    def _extract_taxonomy(self, zip_path: Path, extract_dir: Path) -> None:
        """Extract a taxonomy ZIP file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            logger.info(f"Extracted {zip_path.name} to {extract_dir}")
        except Exception as e:
            logger.error(f"Failed to extract {zip_path}: {e}")
            raise
    
    def _generate_schema_mappings(self) -> None:
        """Generate schema path mappings for Arelle"""
        self._schema_mappings = {}
        
        for taxonomy in self._taxonomies:
            if not taxonomy.taxonomy_type == "tifrs":
                continue  # Skip TW-GAAP for now
            
            # Derive schema filename from taxonomy filename
            # tifrs-20200630.zip -> tifrs-ci-cr-2020-06-30.xsd
            match = re.match(r'tifrs-(\d{4})(\d{2})(\d{2})\.zip', taxonomy.filename)
            if not match:
                continue
            
            year, month, day = match.groups()
            schema_name = f"tifrs-ci-cr-{year}-{month}-{day}.xsd"
            
            # Find the schema file in the extracted directory
            extract_dir = self.taxonomy_dir / taxonomy.filename.replace('.zip', '')
            if not extract_dir.exists():
                continue
            
            # Search for the schema file
            for schema_path in extract_dir.rglob(schema_name):
                self._schema_mappings[schema_name] = str(schema_path)
                logger.debug(f"Mapped {schema_name} -> {schema_path}")
                break
        
        logger.info(f"Generated {len(self._schema_mappings)} schema mappings")
    
    def get_schema_mappings(self) -> Dict[str, str]:
        """Get the current schema mappings"""
        if not self._schema_mappings:
            self._generate_schema_mappings()
        return self._schema_mappings
    
    def get_taxonomy_for_period(self, year: int, quarter: int) -> Optional[TaxonomyInfo]:
        """
        Get the appropriate taxonomy for a given reporting period
        
        Args:
            year: 西元年 (e.g., 2024)
            quarter: 季度 1-4
            
        Returns:
            TaxonomyInfo or None if no matching taxonomy
        """
        for taxonomy in self._taxonomies:
            if taxonomy.is_ongoing:
                # Check if period is after start
                if (year > taxonomy.start_year or 
                    (year == taxonomy.start_year and quarter >= taxonomy.start_quarter)):
                    return taxonomy
            else:
                # Check if period is within range
                start = taxonomy.start_year * 10 + taxonomy.start_quarter
                end = (taxonomy.end_year or taxonomy.start_year) * 10 + (taxonomy.end_quarter or taxonomy.start_quarter)
                period = year * 10 + quarter
                
                if start <= period <= end:
                    return taxonomy
        
        return None
    
    def get_local_schema_path(self, schema_ref: str) -> Optional[Path]:
        """
        Get the local path for a schema reference
        
        Args:
            schema_ref: Schema filename (e.g., "tifrs-ci-cr-2020-06-30.xsd")
            
        Returns:
            Local Path or None if not found
        """
        if schema_ref in self._schema_mappings:
            return Path(self._schema_mappings[schema_ref])
        
        # Try to find it in the taxonomy directory
        for path in self.taxonomy_dir.rglob(schema_ref):
            self._schema_mappings[schema_ref] = str(path)
            return path
        
        return None


# Singleton instance
_taxonomy_manager: Optional[TaxonomyManager] = None


def get_taxonomy_manager() -> TaxonomyManager:
    """Get the taxonomy manager singleton"""
    global _taxonomy_manager
    if _taxonomy_manager is None:
        _taxonomy_manager = TaxonomyManager()
    return _taxonomy_manager


async def init_taxonomies() -> None:
    """Initialize taxonomies on startup"""
    manager = get_taxonomy_manager()
    downloaded = await manager.ensure_taxonomies()
    if downloaded:
        logger.info(f"Downloaded {len(downloaded)} new taxonomies: {downloaded}")
    else:
        logger.info("All taxonomies are up to date")
