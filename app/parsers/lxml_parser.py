"""
lxml XBRL Instance Parser

使用 lxml 解析 XBRL Instance Document
當 Arelle 不可用時的 fallback 方案
"""
import io
import logging
from typing import Dict, List, Optional

from lxml import etree

from app.schemas.xbrl import XBRLFact, XBRLContext

logger = logging.getLogger(__name__)


def parse_instance_facts(content: bytes) -> List[XBRLFact]:
    """
    解析 Instance Document 中的 facts
    
    Args:
        content: XBRL Instance XML 的 bytes
        
    Returns:
        List[XBRLFact]
    """
    facts: List[XBRLFact] = []
    
    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()
        
        # 遍歷所有元素尋找 fact
        for elem in root.iter():
            context_ref = elem.get("contextRef")
            if context_ref:
                # 這是一個 fact
                concept = etree.QName(elem.tag).localname
                facts.append(XBRLFact(
                    concept=concept,
                    value=elem.text,
                    unit=elem.get("unitRef"),
                    context_ref=context_ref,
                    decimals=int(elem.get("decimals")) if elem.get("decimals") else None,
                ))
                
        logger.info(f"Parsed {len(facts)} facts from instance")
        
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in instance document: {e}")
    
    return facts


def parse_instance_contexts(content: bytes) -> Dict[str, XBRLContext]:
    """
    解析 Instance Document 中的 contexts
    
    Args:
        content: XBRL Instance XML 的 bytes
        
    Returns:
        Dict[context_id, XBRLContext]
    """
    contexts: Dict[str, XBRLContext] = {}
    
    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()
        
        for ctx in root.iter("{http://www.xbrl.org/2003/instance}context"):
            ctx_id = ctx.get("id", "")
            
            # 提取 entity
            entity_elem = ctx.find(".//{http://www.xbrl.org/2003/instance}identifier")
            entity = entity_elem.text if entity_elem is not None else ""
            
            # 提取 period
            instant: Optional[str] = None
            start_date: Optional[str] = None
            end_date: Optional[str] = None
            
            instant_elem = ctx.find(".//{http://www.xbrl.org/2003/instance}instant")
            if instant_elem is not None:
                instant = instant_elem.text
            else:
                start_elem = ctx.find(".//{http://www.xbrl.org/2003/instance}startDate")
                end_elem = ctx.find(".//{http://www.xbrl.org/2003/instance}endDate")
                if start_elem is not None:
                    start_date = start_elem.text
                if end_elem is not None:
                    end_date = end_elem.text
            
            contexts[ctx_id] = XBRLContext(
                context_id=ctx_id,
                entity=entity,
                period_start=start_date,
                period_end=end_date,
                instant=instant,
            )
            
        logger.info(f"Parsed {len(contexts)} contexts from instance")
        
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error parsing contexts: {e}")
    
    return contexts
