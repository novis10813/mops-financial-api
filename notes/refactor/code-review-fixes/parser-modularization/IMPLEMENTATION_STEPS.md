# Implementation Steps: Parser Modularization

## Checklist

### Phase 0: 特徵測試 (先寫測試)
- [ ] 新增 `tests/test_xbrl_parser_behavior.py`
- [ ] 測試 `parse()` 基本功能
- [ ] 測試 Calculation Linkbase weight 提取
- [ ] 測試 iXBRL fact 解析
- [ ] 測試 labels 中英文提取
- [ ] 執行測試確認通過

### Phase 1: 建立 parsers 模組
- [ ] 建立 `app/parsers/__init__.py`
- [ ] 建立 `app/parsers/linkbase.py` (最獨立，先拆)
- [ ] 更新 `xbrl_parser.py` 使用新模組
- [ ] 執行測試確認通過

### Phase 2: 拆分 lxml 解析
- [ ] 建立 `app/parsers/lxml_parser.py`
- [ ] 更新 `xbrl_parser.py`
- [ ] 執行測試確認通過

### Phase 3: 拆分 Arelle 解析
- [ ] 建立 `app/parsers/arelle.py`
- [ ] 更新 `xbrl_parser.py`
- [ ] 執行測試確認通過

### Phase 4: 拆分 iXBRL 解析
- [ ] 建立 `app/parsers/ixbrl.py`
- [ ] 更新 `xbrl_parser.py`
- [ ] 執行測試確認通過

### Phase 5: 最終驗證
- [ ] 執行所有測試 (包含會計恆等式)
- [ ] 確認 `xbrl_parser.py` < 200 行
- [ ] 原子化 commit

---

## Step-by-Step Details

### Phase 0: 特徵測試

```python
# tests/test_xbrl_parser_behavior.py

import pytest
from app.services.xbrl_parser import XBRLParser, get_xbrl_parser

class TestXBRLParserBehavior:
    """
    特徵測試：捕捉目前 XBRLParser 的確切行為
    重構後這些測試必須全部通過
    """
    
    def test_parser_singleton(self):
        """確認 singleton 模式正常"""
        p1 = get_xbrl_parser()
        p2 = get_xbrl_parser()
        assert p1 is p2
    
    def test_parse_calculation_linkbase_weights(self):
        """測試 weight 屬性正確提取（這是核心邏輯）"""
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
        
        assert "GrossProfit" in result
        assert len(result["GrossProfit"]) == 2
        
        # 核心：weight 必須正確
        arcs = {arc.to_concept: arc for arc in result["GrossProfit"]}
        assert arcs["OperatingRevenue"].weight == 1.0
        assert arcs["OperatingCosts"].weight == -1.0
    
    def test_find_instance_file_ixbrl(self):
        """測試找出 iXBRL instance 檔案"""
        parser = XBRLParser()
        
        files = {
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_cal.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3_pre.xml": b"",
            "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm": b"",
        }
        
        result = parser._find_instance_file(files)
        assert result == "tifrs-fr0-m1-ci-cr-2330-2024Q3.htm"
```

### Phase 1: Linkbase 模組

```python
# app/parsers/linkbase.py

"""
Linkbase 解析模組
處理 Calculation, Presentation, Label Linkbase
"""
import io
import logging
from typing import Dict, List
from lxml import etree

from app.schemas.xbrl import CalculationArc, PresentationArc

logger = logging.getLogger(__name__)


def parse_calculation_linkbase(content: bytes) -> Dict[str, List[CalculationArc]]:
    """解析 Calculation Linkbase XML"""
    # ... 從 xbrl_parser.py 移植 ...


def parse_presentation_linkbase(content: bytes) -> Dict[str, List[PresentationArc]]:
    """解析 Presentation Linkbase XML"""
    # ... 從 xbrl_parser.py 移植 ...


def parse_label_linkbase(content: bytes) -> tuple[Dict[str, str], Dict[str, str]]:
    """解析 Label Linkbase XML"""
    # ... 從 xbrl_parser.py 移植 ...
```

### 後續 Phase 類似模式

每個 phase：
1. 建立新模組
2. 移植相關方法
3. 更新 `xbrl_parser.py` 的 import 和呼叫
4. 執行測試確認通過
