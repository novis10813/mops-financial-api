"""
Linkbase 解析模組

處理 XBRL Linkbase 檔案：
- Calculation Linkbase (加減邏輯)
- Presentation Linkbase (階層結構)
- Label Linkbase (標籤)
"""
import io
import logging
from typing import Dict, List, Tuple

from lxml import etree

from app.schemas.xbrl import CalculationArc, PresentationArc

logger = logging.getLogger(__name__)


def parse_calculation_linkbase(content: bytes) -> Dict[str, List[CalculationArc]]:
    """
    解析 Calculation Linkbase XML
    
    這是核心邏輯：從這裡取得 weight 屬性來判斷加減
    - weight = 1.0 表示加
    - weight = -1.0 表示減
    
    Args:
        content: Calculation Linkbase XML 的 bytes
        
    Returns:
        Dict[parent_concept, List[CalculationArc]]
    """
    result: Dict[str, List[CalculationArc]] = {}
    
    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()
        
        # 找出所有 calculationArc
        for arc in root.iter("{http://www.xbrl.org/2003/linkbase}calculationArc"):
            from_attr = arc.get("{http://www.w3.org/1999/xlink}from", "")
            to_attr = arc.get("{http://www.w3.org/1999/xlink}to", "")
            weight = float(arc.get("weight", "1.0"))
            order = float(arc.get("order", "0.0"))
            
            if from_attr:
                if from_attr not in result:
                    result[from_attr] = []
                result[from_attr].append(CalculationArc(
                    from_concept=from_attr,
                    to_concept=to_attr,
                    weight=weight,
                    order=order,
                ))
                
        logger.info(f"Parsed {sum(len(v) for v in result.values())} calculation arcs")
        
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in calculation linkbase: {e}")
    
    return result


def parse_presentation_linkbase(content: bytes) -> Dict[str, List[PresentationArc]]:
    """
    解析 Presentation Linkbase XML
    
    Presentation linkbase 定義報表的階層結構
    
    Args:
        content: Presentation Linkbase XML 的 bytes
        
    Returns:
        Dict[parent_concept, List[PresentationArc]]
    """
    result: Dict[str, List[PresentationArc]] = {}
    
    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()
        
        for arc in root.iter("{http://www.xbrl.org/2003/linkbase}presentationArc"):
            from_attr = arc.get("{http://www.w3.org/1999/xlink}from", "")
            to_attr = arc.get("{http://www.w3.org/1999/xlink}to", "")
            order = float(arc.get("order", "0.0"))
            preferred_label = arc.get("preferredLabel")
            
            if from_attr:
                if from_attr not in result:
                    result[from_attr] = []
                result[from_attr].append(PresentationArc(
                    from_concept=from_attr,
                    to_concept=to_attr,
                    order=order,
                    preferred_label=preferred_label,
                ))
                
        logger.info(f"Parsed {sum(len(v) for v in result.values())} presentation arcs")
        
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in presentation linkbase: {e}")
    
    return result


def parse_label_linkbase(content: bytes) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    解析 Label Linkbase XML
    
    提取中英文標籤
    
    Args:
        content: Label Linkbase XML 的 bytes
        
    Returns:
        (labels_zh, labels_en) 兩個字典
    """
    labels_zh: Dict[str, str] = {}
    labels_en: Dict[str, str] = {}
    
    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()
        
        for label in root.iter("{http://www.xbrl.org/2003/linkbase}label"):
            label_text = label.text or ""
            lang = label.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            
            # 找對應的 loc 來取得 concept
            # 這裡簡化處理，實際需要透過 labelArc 連結
            xlink_label = label.get("{http://www.w3.org/1999/xlink}label", "")
            
            if "zh" in lang.lower() or "tw" in lang.lower():
                labels_zh[xlink_label] = label_text
            elif "en" in lang.lower():
                labels_en[xlink_label] = label_text
                
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in label linkbase: {e}")
    
    return labels_zh, labels_en
