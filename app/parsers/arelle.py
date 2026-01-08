"""
Arelle XBRL Extractor

使用 Arelle 庫提取 XBRL 資料
Arelle 提供完整的 XBRL 解析功能，包括 Taxonomy 載入
"""
import logging
from typing import Dict, List, Tuple, Optional, Any

from app.schemas.xbrl import CalculationArc, PresentationArc, XBRLFact, XBRLContext

logger = logging.getLogger(__name__)


def check_arelle_available() -> bool:
    """檢查 Arelle 是否可用"""
    try:
        from arelle import Cntlr
        return True
    except ImportError:
        return False


def extract_calculation_arcs(model_xbrl: Any) -> Dict[str, List[CalculationArc]]:
    """
    使用 Arelle 提取 Calculation Arcs
    
    Args:
        model_xbrl: Arelle ModelXbrl 物件
        
    Returns:
        Dict[parent_concept, List[CalculationArc]]
    """
    result: Dict[str, List[CalculationArc]] = {}
    
    try:
        from arelle import XbrlConst
        
        for rel in model_xbrl.relationshipSet(XbrlConst.summationItem).modelRelationships:
            from_concept = rel.fromModelObject.qname.localName
            to_concept = rel.toModelObject.qname.localName
            
            if from_concept not in result:
                result[from_concept] = []
            
            result[from_concept].append(CalculationArc(
                from_concept=from_concept,
                to_concept=to_concept,
                weight=rel.weight,
                order=rel.order or 0.0,
            ))
    except Exception as e:
        logger.error(f"Error extracting calculation arcs with Arelle: {e}")
    
    return result


def extract_presentation_arcs(model_xbrl: Any) -> Dict[str, List[PresentationArc]]:
    """
    使用 Arelle 提取 Presentation Arcs
    
    Args:
        model_xbrl: Arelle ModelXbrl 物件
        
    Returns:
        Dict[parent_concept, List[PresentationArc]]
    """
    result: Dict[str, List[PresentationArc]] = {}
    
    try:
        from arelle import XbrlConst
        
        for rel in model_xbrl.relationshipSet(XbrlConst.parentChild).modelRelationships:
            from_concept = rel.fromModelObject.qname.localName
            to_concept = rel.toModelObject.qname.localName
            
            if from_concept not in result:
                result[from_concept] = []
            
            result[from_concept].append(PresentationArc(
                from_concept=from_concept,
                to_concept=to_concept,
                order=rel.order or 0.0,
                preferred_label=rel.preferredLabel,
            ))
    except Exception as e:
        logger.error(f"Error extracting presentation arcs with Arelle: {e}")
    
    return result


def extract_facts(model_xbrl: Any) -> List[XBRLFact]:
    """
    使用 Arelle 提取 Facts
    
    Args:
        model_xbrl: Arelle ModelXbrl 物件
        
    Returns:
        List[XBRLFact]
    """
    facts: List[XBRLFact] = []
    
    try:
        for fact in model_xbrl.facts:
            facts.append(XBRLFact(
                concept=fact.qname.localName,
                value=str(fact.value) if fact.value is not None else None,
                unit=fact.unit.id if fact.unit is not None else None,
                context_ref=fact.context.id if fact.context is not None else "",
                decimals=fact.decimals if hasattr(fact, 'decimals') else None,
            ))
    except Exception as e:
        logger.error(f"Error extracting facts with Arelle: {e}")
    
    return facts


def extract_contexts(model_xbrl: Any) -> Dict[str, XBRLContext]:
    """
    使用 Arelle 提取 Contexts
    
    Args:
        model_xbrl: Arelle ModelXbrl 物件
        
    Returns:
        Dict[context_id, XBRLContext]
    """
    contexts: Dict[str, XBRLContext] = {}
    
    try:
        for ctx in model_xbrl.contexts.values():
            contexts[ctx.id] = XBRLContext(
                context_id=ctx.id,
                entity=ctx.entityIdentifier[1] if ctx.entityIdentifier else "",
                period_start=str(ctx.startDatetime) if ctx.startDatetime else None,
                period_end=str(ctx.endDatetime) if ctx.endDatetime else None,
                instant=str(ctx.instantDatetime) if ctx.isInstantPeriod else None,
            )
    except Exception as e:
        logger.error(f"Error extracting contexts with Arelle: {e}")
    
    return contexts


def extract_labels(model_xbrl: Any) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    使用 Arelle 提取 Labels
    
    Args:
        model_xbrl: Arelle ModelXbrl 物件
        
    Returns:
        (labels_zh, labels_en) 兩個字典
    """
    labels_zh: Dict[str, str] = {}
    labels_en: Dict[str, str] = {}
    
    try:
        for concept in model_xbrl.qnameConcepts.values():
            name = concept.qname.localName
            
            # 嘗試取得中文標籤
            label_zh = concept.label(lang="zh-TW") or concept.label(lang="zh")
            if label_zh:
                labels_zh[name] = label_zh
            
            # 嘗試取得英文標籤  
            label_en = concept.label(lang="en")
            if label_en:
                labels_en[name] = label_en
                
    except Exception as e:
        logger.error(f"Error extracting labels with Arelle: {e}")
    
    return labels_zh, labels_en
