"""
Tests for XBRL Parser
"""
import pytest
from app.services.xbrl_parser import XBRLParser


class TestXBRLParser:
    """Test XBRL Parser functionality"""
    
    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = XBRLParser()
        assert parser is not None
    
    def test_parse_calculation_linkbase_empty(self):
        """Test parsing empty calculation linkbase"""
        parser = XBRLParser()
        
        # Empty XML
        empty_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase">
        </linkbase>
        """
        
        result = parser._parse_calculation_linkbase(empty_xml)
        assert result == {}
    
    def test_parse_calculation_linkbase_with_arcs(self):
        """Test parsing calculation linkbase with valid arcs"""
        parser = XBRLParser()
        
        # Sample calculation linkbase with weight attributes
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
            <calculationLink>
                <calculationArc 
                    xlink:from="GrossProfit" 
                    xlink:to="OperatingRevenue" 
                    weight="1.0"
                    order="1.0"/>
                <calculationArc 
                    xlink:from="GrossProfit" 
                    xlink:to="OperatingCosts" 
                    weight="-1.0"
                    order="2.0"/>
            </calculationLink>
        </linkbase>
        """
        
        result = parser._parse_calculation_linkbase(sample_xml)
        
        # Should have one parent (GrossProfit) with two children
        assert "GrossProfit" in result
        assert len(result["GrossProfit"]) == 2
        
        # Check weights (the core logic for add/subtract)
        arcs = result["GrossProfit"]
        revenue_arc = next(a for a in arcs if a.to_concept == "OperatingRevenue")
        cost_arc = next(a for a in arcs if a.to_concept == "OperatingCosts")
        
        assert revenue_arc.weight == 1.0  # Add
        assert cost_arc.weight == -1.0    # Subtract
    
    def test_find_instance_file(self):
        """Test finding instance file in ZIP contents"""
        parser = XBRLParser()
        
        files = {
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_cal.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_pre.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm": b"",  # iXBRL instance
        }
        
        result = parser._find_instance_file(files)
        assert result == "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm"
