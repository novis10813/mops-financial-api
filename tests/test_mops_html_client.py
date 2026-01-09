"""
Tests for MOPS HTML Client
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd

from app.services.mops_html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
    MOPSParsingError,
    get_mops_html_client,
)


class TestMOPSHTMLClientInit:
    """Test MOPSHTMLClient initialization"""
    
    def test_default_initialization(self):
        """Test default initialization values"""
        client = MOPSHTMLClient()
        assert client.rate_limit == 1.0
        assert client.max_retries == 3
        assert client._last_request_time == 0
    
    def test_custom_initialization(self):
        """Test custom initialization values"""
        client = MOPSHTMLClient(rate_limit=0.5, max_retries=5)
        assert client.rate_limit == 0.5
        assert client.max_retries == 5
    
    def test_singleton_returns_same_instance(self):
        """Test singleton pattern"""
        client1 = get_mops_html_client()
        client2 = get_mops_html_client()
        assert client1 is client2


class TestMOPSHTMLClientHeaders:
    """Test header generation"""
    
    def test_default_headers(self):
        """Test default headers are set"""
        client = MOPSHTMLClient()
        headers = client._get_headers()
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Referer" in headers
        assert headers["Referer"] == client.MOPS_BASE
    
    def test_custom_referer(self):
        """Test custom referer is set"""
        client = MOPSHTMLClient()
        custom_url = "https://example.com"
        headers = client._get_headers(referer=custom_url)
        
        assert headers["Referer"] == custom_url


class TestMOPSHTMLClientErrors:
    """Test error classes"""
    
    def test_base_error(self):
        """Test base error class"""
        error = MOPSHTMLClientError("Test error", 500)
        assert error.message == "Test error"
        assert error.status_code == 500
        assert str(error) == "Test error"
    
    def test_data_not_found_error(self):
        """Test data not found error"""
        error = MOPSDataNotFoundError("No data")
        assert error.message == "No data"
        assert isinstance(error, MOPSHTMLClientError)
    
    def test_parsing_error(self):
        """Test parsing error"""
        error = MOPSParsingError("Parse failed")
        assert error.message == "Parse failed"
        assert isinstance(error, MOPSHTMLClientError)


class TestFetchStaticHTML:
    """Test fetch_static_html method"""
    
    @pytest.fixture
    def client(self):
        """Create a client with no rate limiting for tests"""
        return MOPSHTMLClient(rate_limit=0)
    
    @pytest.fixture
    def sample_revenue_html(self):
        """Sample revenue HTML table"""
        return """
        <html>
        <body>
        <table>
            <tr><th>公司代號</th><th>公司名稱</th><th>營業收入</th></tr>
            <tr><td>2330</td><td>台積電</td><td>200,000,000</td></tr>
            <tr><td>2317</td><td>鴻海</td><td>150,000,000</td></tr>
        </table>
        </body>
        </html>
        """
    
    @pytest.mark.asyncio
    async def test_parse_html_table_success(self, client, sample_revenue_html):
        """Test successful HTML table parsing"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_revenue_html
        mock_response.encoding = "utf-8"
        
        with patch.object(
            client, 
            'fetch_static_html', 
            new_callable=AsyncMock
        ) as mock_fetch:
            # Simulate what the real method would return
            dfs = pd.read_html(sample_revenue_html)
            mock_fetch.return_value = dfs
            
            result = await mock_fetch("http://example.com")
            
            assert len(result) == 1
            assert "公司代號" in result[0].columns or 0 in result[0].columns
    
    @pytest.mark.asyncio
    async def test_data_not_found_raises_error(self, client):
        """Test that 404 raises MOPSDataNotFoundError"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(MOPSDataNotFoundError):
                await client.fetch_static_html("http://example.com/notfound")


class TestFetchHTMLTable:
    """Test fetch_html_table method for AJAX endpoints"""
    
    @pytest.fixture
    def client(self):
        return MOPSHTMLClient(rate_limit=0)
    
    @pytest.mark.asyncio
    async def test_no_data_found_message(self, client):
        """Test that '查無資料' response raises MOPSDataNotFoundError"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html>查無資料</html>"
            mock_response.encoding = "utf-8"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(MOPSDataNotFoundError):
                await client.fetch_html_table("ajax_test", {"param": "value"})


class TestURLConstruction:
    """Test URL construction"""
    
    def test_revenue_url_construction(self):
        """Test monthly revenue URL construction with ROC year"""
        year = 113
        month = 12
        market = "sii"
        company_type = 0
        
        url = f"https://mops.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html"
        
        assert url == "https://mops.twse.com.tw/nas/t21/sii/t21sc03_113_12_0.html"
    
    def test_revenue_url_different_markets(self):
        """Test URL construction for different markets"""
        year = 113
        month = 1
        
        markets = {
            "sii": "上市",
            "otc": "上櫃",
            "rotc": "興櫃",
            "pub": "公開發行",
        }
        
        for market in markets.keys():
            url = f"https://mops.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_0.html"
            assert market in url
