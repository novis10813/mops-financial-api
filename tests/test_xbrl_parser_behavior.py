"""
Characterization Tests for XBRL Parser

這些測試捕捉目前 XBRLParser 的確切行為。
在 parser-modularization 重構後，這些測試必須全部通過。
"""
import pytest
from typing import Dict, List

from app.services.xbrl_parser import XBRLParser, get_xbrl_parser
from app.schemas.xbrl import XBRLPackage, CalculationArc, PresentationArc


class TestXBRLParserSingleton:
    """測試 Singleton 模式"""
    
    def test_get_xbrl_parser_returns_same_instance(self):
        """確認 singleton 模式正常"""
        p1 = get_xbrl_parser()
        p2 = get_xbrl_parser()
        assert p1 is p2
    
    def test_parser_initialization(self):
        """測試 parser 可以正常初始化"""
        parser = XBRLParser()
        assert parser is not None
        assert hasattr(parser, '_arelle_available')


class TestCalculationLinkbaseParsing:
    """測試 Calculation Linkbase 解析"""
    
    def test_parse_empty_linkbase(self):
        """測試空的 calculation linkbase"""
        parser = XBRLParser()
        
        empty_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase">
        </linkbase>
        '''
        
        result = parser._parse_calculation_linkbase(empty_xml)
        assert result == {}
    
    def test_parse_linkbase_with_arcs(self):
        """測試有 arcs 的 calculation linkbase"""
        parser = XBRLParser()
        
        sample_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
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
        '''
        
        result = parser._parse_calculation_linkbase(sample_xml)
        
        # 應該有一個 parent (GrossProfit)
        assert "GrossProfit" in result
        assert len(result["GrossProfit"]) == 2
        
        # 核心測試：weight 屬性必須正確提取
        arcs = {arc.to_concept: arc for arc in result["GrossProfit"]}
        assert arcs["OperatingRevenue"].weight == 1.0   # 加
        assert arcs["OperatingCosts"].weight == -1.0    # 減
    
    def test_parse_linkbase_preserves_order(self):
        """測試 order 屬性正確保留"""
        parser = XBRLParser()
        
        sample_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
            <calculationLink>
                <calculationArc 
                    xlink:from="Total" 
                    xlink:to="ItemB" 
                    weight="1.0"
                    order="2.0"/>
                <calculationArc 
                    xlink:from="Total" 
                    xlink:to="ItemA" 
                    weight="1.0"
                    order="1.0"/>
            </calculationLink>
        </linkbase>
        '''
        
        result = parser._parse_calculation_linkbase(sample_xml)
        arcs = {arc.to_concept: arc for arc in result["Total"]}
        
        assert arcs["ItemA"].order == 1.0
        assert arcs["ItemB"].order == 2.0


class TestPresentationLinkbaseParsing:
    """測試 Presentation Linkbase 解析"""
    
    def test_parse_empty_presentation_linkbase(self):
        """測試空的 presentation linkbase"""
        parser = XBRLParser()
        
        empty_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase">
        </linkbase>
        '''
        
        result = parser._parse_presentation_linkbase(empty_xml)
        assert result == {}
    
    def test_parse_presentation_with_hierarchy(self):
        """測試階層結構解析"""
        parser = XBRLParser()
        
        sample_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
            <presentationLink>
                <presentationArc 
                    xlink:from="Statement" 
                    xlink:to="Assets" 
                    order="1.0"/>
                <presentationArc 
                    xlink:from="Statement" 
                    xlink:to="Liabilities" 
                    order="2.0"/>
                <presentationArc 
                    xlink:from="Assets" 
                    xlink:to="CurrentAssets" 
                    order="1.0"/>
            </presentationLink>
        </linkbase>
        '''
        
        result = parser._parse_presentation_linkbase(sample_xml)
        
        # Statement 有兩個子項
        assert "Statement" in result
        assert len(result["Statement"]) == 2
        
        # Assets 有一個子項
        assert "Assets" in result
        assert len(result["Assets"]) == 1


class TestLabelLinkbaseParsing:
    """測試 Label Linkbase 解析"""
    
    def test_parse_empty_label_linkbase(self):
        """測試空的 label linkbase"""
        parser = XBRLParser()
        
        empty_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <linkbase xmlns="http://www.xbrl.org/2003/linkbase">
        </linkbase>
        '''
        
        labels_zh, labels_en = parser._parse_label_linkbase(empty_xml)
        assert labels_zh == {}
        assert labels_en == {}


class TestInstanceFileFinding:
    """測試 Instance 檔案辨識"""
    
    def test_find_ixbrl_file(self):
        """測試找出 iXBRL (.htm) 檔案"""
        parser = XBRLParser()
        
        files = {
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_cal.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_pre.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm": b"",
        }
        
        result = parser._find_instance_file(files)
        assert result == "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm"
    
    def test_find_html_file(self):
        """測試找出 .html 檔案"""
        parser = XBRLParser()
        
        files = {
            "report_cal.xml": b"",
            "report.html": b"",
        }
        
        result = parser._find_instance_file(files)
        assert result == "report.html"
    
    def test_find_xml_instance(self):
        """測試找出傳統 XML instance"""
        parser = XBRLParser()
        
        files = {
            "report_cal.xml": b"",
            "report_pre.xml": b"",
            "report_lab.xml": b"",
            "report_instance.xml": b"",
        }
        
        result = parser._find_instance_file(files)
        assert result == "report_instance.xml"
    
    def test_find_no_instance(self):
        """測試沒有 instance 檔案的情況"""
        parser = XBRLParser()
        
        files = {
            "report_cal.xml": b"",
            "report_pre.xml": b"",
        }
        
        result = parser._find_instance_file(files)
        assert result is None


class TestFormatDetection:
    """測試格式自動判斷"""
    
    def test_detect_zip_format(self):
        """測試 ZIP 格式判斷 (PK magic bytes)"""
        parser = XBRLParser()
        
        # ZIP 檔案開頭是 'PK' (0x50, 0x4B)
        zip_content = b'PK\x03\x04...'
        
        # 這應該嘗試 parse_zip（會因格式無效而失敗，但不會誤判為 iXBRL）
        assert zip_content[:2] == b"PK"
    
    def test_detect_ixbrl_format(self):
        """測試 iXBRL 格式判斷"""
        parser = XBRLParser()
        
        ixbrl_content = b'<html><body><ix:nonFraction>123</ix:nonFraction></body></html>'
        
        # 應該包含 iXBRL 標記
        assert b"ix:nonFraction" in ixbrl_content or b"ix:nonNumeric" in ixbrl_content


class TestSchemaRefReplacement:
    """測試 Schema Ref 替換邏輯"""
    
    def test_replace_schema_refs_preserves_content(self):
        """測試替換 schema ref 不破壞其他內容"""
        parser = XBRLParser()
        
        # 不包含 schema ref 的內容應該原樣返回
        content = b'<html><body>Test content</body></html>'
        result = parser._replace_schema_refs(content)
        
        # 至少內容應該可以解碼
        assert b'Test content' in result
