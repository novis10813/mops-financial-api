"""
Integration Tests for Additional Crawlers

Tests the full API endpoints using TestClient.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestAppStartup:
    """Test application startup"""
    
    def test_app_root(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200


class TestRevenueEndpoints:
    """Test revenue API endpoints"""
    
    def test_revenue_endpoint_exists(self):
        """Test that revenue endpoints are registered"""
        # This tests the endpoint exists (will fail validation but return 422)
        response = client.get("/api/v1/revenue/monthly")
        assert response.status_code == 422  # Missing required params
    
    def test_revenue_invalid_year(self):
        """Test revenue with invalid year"""
        response = client.get("/api/v1/revenue/monthly", params={
            "year": 50,  # Too low
            "month": 12,
        })
        assert response.status_code == 422
    
    def test_revenue_invalid_month(self):
        """Test revenue with invalid month"""
        response = client.get("/api/v1/revenue/monthly", params={
            "year": 113,
            "month": 15,  # Invalid
        })
        assert response.status_code == 422


class TestInsidersEndpoints:
    """Test insiders API endpoints"""
    
    def test_pledge_endpoint_exists(self):
        """Test that pledge endpoints are registered"""
        response = client.get("/api/v1/insiders/pledge")
        assert response.status_code == 422  # Missing params
    
    def test_pledge_path_param(self):
        """Test pledge with path parameter"""
        response = client.get("/api/v1/insiders/pledge/2330", params={
            "year": 113,
            "month": 12,
        })
        # May timeout or return 400 if no real connection
        assert response.status_code in [200, 400, 422, 500]


class TestDividendEndpoints:
    """Test dividend API endpoints"""
    
    def test_dividend_endpoint_exists(self):
        """Test that dividend endpoints are registered"""
        response = client.get("/api/v1/dividend/2330", params={
            "year_start": 112,
        })
        # May timeout or return 400 if no real connection
        assert response.status_code in [200, 400, 422, 500]
    
    def test_dividend_summary_endpoint(self):
        """Test dividend summary endpoint"""
        response = client.get("/api/v1/dividend/2330/summary", params={
            "year": 112,
        })
        assert response.status_code in [200, 400, 422, 500]


class TestDisclosureEndpoints:
    """Test disclosure API endpoints"""
    
    def test_disclosure_endpoint_exists(self):
        """Test that disclosure endpoints are registered"""
        response = client.get("/api/v1/disclosure")
        assert response.status_code == 422  # Missing params
    
    def test_disclosure_path_param(self):
        """Test disclosure with path param"""
        response = client.get("/api/v1/disclosure/2317", params={
            "year": 112,
            "month": 12,
        })
        assert response.status_code in [200, 400, 422, 500]


class TestOpenAPISpec:
    """Test OpenAPI specification"""
    
    def test_openapi_json(self):
        """Test that OpenAPI spec is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        spec = response.json()
        assert "openapi" in spec
        assert "paths" in spec
    
    def test_swagger_ui(self):
        """Test that Swagger UI is available"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_new_endpoints_in_spec(self):
        """Test that new endpoints are in OpenAPI spec"""
        response = client.get("/openapi.json")
        spec = response.json()
        paths = spec["paths"]
        
        # Check new endpoints exist
        assert "/api/v1/revenue/monthly" in paths
        assert "/api/v1/insiders/pledge/{stock_id}" in paths
        assert "/api/v1/dividend/{stock_id}" in paths
        assert "/api/v1/disclosure/{stock_id}" in paths


class TestRouterTags:
    """Test router tags for API organization"""
    
    def test_tags_in_spec(self):
        """Test that tags are properly set"""
        response = client.get("/openapi.json")
        spec = response.json()
        
        # Get all tags used
        tags_used = set()
        for path_data in spec["paths"].values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "tags" in method_data:
                    tags_used.update(method_data["tags"])
        
        # Check new tags exist
        assert "revenue" in tags_used
        assert "insiders" in tags_used
        assert "dividend" in tags_used
        assert "disclosure" in tags_used
