"""
XBRL Parser using Arelle
Parses XBRL instance documents and linkbases
"""
import io
import logging
import tempfile
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from lxml import etree

from app.schemas.xbrl import (
    XBRLPackage, 
    CalculationArc, 
    PresentationArc, 
    XBRLFact, 
    XBRLContext
)

logger = logging.getLogger(__name__)

# XBRL namespaces
NAMESPACES = {
    "xbrli": "http://www.xbrl.org/2003/instance",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "ix": "http://www.xbrl.org/2013/inlineXBRL",
    "ixt": "http://www.xbrl.org/inlineXBRL/transformation/2015-02-26",
}


class XBRLParserError(Exception):
    """XBRL Parser Error"""
    pass


class XBRLParser:
    """
    XBRL 解析器
    
    使用 Arelle 進行完整的 XBRL 解析，
    包含 Calculation Linkbase 的 weight 屬性（加減邏輯）
    """
    
    def __init__(self):
        self._arelle_available = self._check_arelle()
        if not self._arelle_available:
            logger.warning("Arelle not available, falling back to lxml parsing")
    
    def _check_arelle(self) -> bool:
        """檢查 Arelle 是否可用"""
        try:
            from arelle import Cntlr
            return True
        except ImportError:
            return False
    
    def parse_zip(
        self, 
        zip_content: bytes, 
        stock_id: str, 
        year: int, 
        quarter: int
    ) -> XBRLPackage:
        """
        解析 XBRL ZIP 包
        
        Args:
            zip_content: ZIP 檔案的 bytes
            stock_id: 股票代號
            year: 民國年
            quarter: 季度
        
        Returns:
            XBRLPackage 包含解析後的所有資料
        """
        # 解壓縮到暫存目錄
        from app.services.mops_client import get_mops_client
        client = get_mops_client()
        files = client.extract_zip(zip_content)
        
        logger.info(f"Extracted {len(files)} files from XBRL ZIP")
        for filename in files.keys():
            logger.debug(f"  - {filename}")
        
        # 建立基本 package
        package = XBRLPackage(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
        )
        
        # 根據 Arelle 可用性選擇解析方式
        if self._arelle_available:
            return self._parse_with_arelle(files, package)
        else:
            return self._parse_with_lxml(files, package)
    
    def parse_ixbrl(
        self,
        ixbrl_content: bytes,
        stock_id: str,
        year: int,
        quarter: int
    ) -> XBRLPackage:
        """
        解析 iXBRL (Inline XBRL) HTML 檔案
        
        這是 MOPS 2019 年後使用的格式，XBRL 標籤嵌入在 HTML 中
        
        Args:
            ixbrl_content: iXBRL HTML 檔案的 bytes
            stock_id: 股票代號
            year: 民國年
            quarter: 季度
        
        Returns:
            XBRLPackage 包含解析後的所有資料
        """
        package = XBRLPackage(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
        )
        
        # 1. 優先嘗試 Arelle (支援從 schemaRef 取得 linkbase)
        if self._arelle_available:
            try:
                return self._parse_ixbrl_with_arelle(ixbrl_content, package)
            except Exception as e:
                logger.warning(f"Arelle parsing failed for iXBRL, falling back to lxml: {e}")
        
        # 2. 降級使用 lxml (僅提取 facts/contexts，無 hierarchy/calculation)
        try:
            # 解析 HTML (使用 HTML parser 而非 XML parser)
            parser = etree.HTMLParser(encoding='utf-8')
            tree = etree.parse(io.BytesIO(ixbrl_content), parser)
            root = tree.getroot()
            
            # 定義 iXBRL 命名空間
            ix_ns = "http://www.xbrl.org/2013/inlineXBRL"
            xbrli_ns = "http://www.xbrl.org/2003/instance"
            
            # ... (原有 lxml 邏輯保持不變) ...
            
            # 1. 提取數值型 Facts (ix:nonFraction)
            # 注意: HTML parser 會將標籤和屬性轉為小寫
            facts = []
            for elem in root.iter():
                tag_lower = str(elem.tag).lower()
                
                # 處理 ix:nonfraction (數值) - 注意小寫
                if 'nonfraction' in tag_lower:
                    name = elem.get("name", "")
                    # HTML parser 轉為小寫: contextref 而非 contextRef
                    context_ref = elem.get("contextref", "") or elem.get("contextRef", "")
                    unit_ref = elem.get("unitref") or elem.get("unitRef")
                    scale = elem.get("scale", "0")
                    decimals = elem.get("decimals")
                    
                    # 取得原始值並根據 scale 調整
                    raw_value = elem.text or ""
                    # 移除數字格式中的逗號
                    raw_value = raw_value.replace(",", "")
                    
                    # 從 name 中提取 concept (格式: namespace:concept)
                    concept = name.split(":")[-1] if ":" in name else name
                    
                    facts.append(XBRLFact(
                        concept=concept,
                        value=raw_value,
                        unit=unit_ref,
                        context_ref=context_ref,
                        decimals=int(decimals) if decimals and decimals.lstrip('-').isdigit() else None,
                    ))
                
                # 處理 ix:nonnumeric (文字) - 注意小寫
                elif 'nonnumeric' in tag_lower:
                    name = elem.get("name", "")
                    context_ref = elem.get("contextref", "") or elem.get("contextRef", "")
                    
                    concept = name.split(":")[-1] if ":" in name else name
                    
                    facts.append(XBRLFact(
                        concept=concept,
                        value=elem.text,
                        unit=None,
                        context_ref=context_ref,
                        decimals=None,
                    ))
            
            package.facts = facts
            logger.info(f"Parsed {len(facts)} facts from iXBRL with lxml")
            
            # 2. 提取 Contexts (在 ix:header > ix:resources 中)
            contexts = {}
            for ctx in root.iter():
                if 'context' in str(ctx.tag).lower() and ctx.get("id"):
                    ctx_id = ctx.get("id", "")
                    
                    # 提取 entity
                    entity = ""
                    for id_elem in ctx.iter():
                        if 'identifier' in str(id_elem.tag).lower():
                            entity = id_elem.text or ""
                            break
                    
                    # 提取 period
                    instant = None
                    start_date = None
                    end_date = None
                    
                    for period_elem in ctx.iter():
                        tag_lower = str(period_elem.tag).lower()
                        if 'instant' in tag_lower:
                            instant = period_elem.text
                        elif 'startdate' in tag_lower:
                            start_date = period_elem.text
                        elif 'enddate' in tag_lower:
                            end_date = period_elem.text
                    
                    contexts[ctx_id] = XBRLContext(
                        context_id=ctx_id,
                        entity=entity,
                        period_start=start_date,
                        period_end=end_date,
                        instant=instant,
                    )
            
            package.contexts = contexts
            logger.info(f"Parsed {len(contexts)} contexts from iXBRL with lxml")
            
        except Exception as e:
            logger.error(f"Error parsing iXBRL with lxml: {e}")
            raise XBRLParserError(f"Failed to parse iXBRL: {e}")
        
        return package

    def _parse_ixbrl_with_arelle(self, content: bytes, package: XBRLPackage) -> XBRLPackage:
        """
        使用 Arelle 解析 iXBRL
        只需將內容寫入暫存檔，Arelle 會自動處理
        """
        from arelle import Cntlr, ModelManager, FileSource
        
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            cntlr = Cntlr.Cntlr(logFileName="logToPrint")
            model_manager = ModelManager.initialize(cntlr)
            
            try:
                # 載入 iXBRL 文件
                model_xbrl = model_manager.load(
                    FileSource.FileSource(tmp_path)
                )
                
                if model_xbrl is None:
                    raise XBRLParserError("Failed to load iXBRL document with Arelle")
                
                # Arelle 會自動解析引用的 schemaRef，所以 Linkbase 應該都在
                package.calculation_arcs = self._extract_calculation_arcs_arelle(model_xbrl)
                package.presentation_arcs = self._extract_presentation_arcs_arelle(model_xbrl)
                package.facts = self._extract_facts_arelle(model_xbrl)
                package.contexts = self._extract_contexts_arelle(model_xbrl)
                package.labels, package.labels_en = self._extract_labels_arelle(model_xbrl)
                
                model_xbrl.close()
                logger.info(f"Successfully parsed iXBRL with Arelle: {len(package.facts)} facts, {len(package.presentation_arcs)} presentation concepts")
                
            finally:
                cntlr.close()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        return package
    
    def parse(
        self,
        content: bytes,
        stock_id: str,
        year: int,
        quarter: int
    ) -> XBRLPackage:
        """
        自動判斷格式並解析
        
        Args:
            content: XBRL/iXBRL 檔案的 bytes (可以是 ZIP 或 HTML)
            stock_id: 股票代號
            year: 民國年
            quarter: 季度
        
        Returns:
            XBRLPackage
        """
        # 判斷格式
        if content[:2] == b"PK":
            # ZIP 格式
            return self.parse_zip(content, stock_id, year, quarter)
        elif b"ix:nonFraction" in content or b"ix:nonNumeric" in content:
            # iXBRL 格式
            return self.parse_ixbrl(content, stock_id, year, quarter)
        else:
            raise XBRLParserError("Unknown file format - expected ZIP or iXBRL HTML")
    
    def _parse_with_arelle(
        self, 
        files: Dict[str, bytes], 
        package: XBRLPackage
    ) -> XBRLPackage:
        """使用 Arelle 解析（完整功能）"""
        from arelle import Cntlr, ModelManager, FileSource
        
        # 找出 instance 文件
        instance_file = self._find_instance_file(files)
        if not instance_file:
            raise XBRLParserError("No instance document found in ZIP")
        
        # 將檔案寫入暫存目錄供 Arelle 讀取
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename, content in files.items():
                filepath = Path(tmpdir) / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(content)
            
            instance_path = Path(tmpdir) / instance_file
            
            # 初始化 Arelle controller
            cntlr = Cntlr.Cntlr(logFileName="logToPrint")
            model_manager = ModelManager.initialize(cntlr)
            
            try:
                # 載入 XBRL 文件
                model_xbrl = model_manager.load(
                    FileSource.FileSource(str(instance_path))
                )
                
                if model_xbrl is None:
                    raise XBRLParserError("Failed to load XBRL document with Arelle")
                
                # 解析 Calculation Linkbase
                package.calculation_arcs = self._extract_calculation_arcs_arelle(model_xbrl)
                
                # 解析 Presentation Linkbase  
                package.presentation_arcs = self._extract_presentation_arcs_arelle(model_xbrl)
                
                # 解析 Facts
                package.facts = self._extract_facts_arelle(model_xbrl)
                
                # 解析 Contexts
                package.contexts = self._extract_contexts_arelle(model_xbrl)
                
                # 解析 Labels
                package.labels, package.labels_en = self._extract_labels_arelle(model_xbrl)
                
                model_xbrl.close()
                
            finally:
                cntlr.close()
        
        return package
    
    def _parse_with_lxml(
        self, 
        files: Dict[str, bytes], 
        package: XBRLPackage
    ) -> XBRLPackage:
        """使用 lxml 解析（基本功能）"""
        # 解析 Calculation Linkbase
        for filename, content in files.items():
            if "_cal" in filename.lower() and filename.endswith(".xml"):
                package.calculation_arcs = self._parse_calculation_linkbase(content)
            elif "_pre" in filename.lower() and filename.endswith(".xml"):
                package.presentation_arcs = self._parse_presentation_linkbase(content)
            elif "_lab" in filename.lower() and filename.endswith(".xml"):
                labels_zh, labels_en = self._parse_label_linkbase(content)
                package.labels.update(labels_zh)
                package.labels_en.update(labels_en)
        
        # 解析 Instance Document
        instance_file = self._find_instance_file(files)
        if instance_file:
            instance_content = files[instance_file]
            package.facts = self._parse_instance_facts(instance_content)
            package.contexts = self._parse_instance_contexts(instance_content)
        
        return package
    
    def _find_instance_file(self, files: Dict[str, bytes]) -> Optional[str]:
        """找出 Instance 文件"""
        for filename in files.keys():
            # iXBRL 格式 (.htm/.html)
            if filename.endswith(('.htm', '.html')):
                return filename
            # 傳統 XBRL 格式 (.xml)
            if filename.endswith('.xml') and not any(
                x in filename.lower() for x in ['_cal', '_pre', '_lab', '_def', '_ref', '.xsd']
            ):
                return filename
        return None
    
    def _parse_calculation_linkbase(self, content: bytes) -> Dict[str, List[CalculationArc]]:
        """
        解析 Calculation Linkbase XML
        這是核心邏輯：從這裡取得 weight 屬性來判斷加減
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
    
    def _parse_presentation_linkbase(self, content: bytes) -> Dict[str, List[PresentationArc]]:
        """解析 Presentation Linkbase XML"""
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
    
    def _parse_label_linkbase(self, content: bytes) -> tuple[Dict[str, str], Dict[str, str]]:
        """解析 Label Linkbase XML"""
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
    
    def _parse_instance_facts(self, content: bytes) -> List[XBRLFact]:
        """解析 Instance Document 中的 facts"""
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
    
    def _parse_instance_contexts(self, content: bytes) -> Dict[str, XBRLContext]:
        """解析 Instance Document 中的 contexts"""
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
                instant = None
                start_date = None
                end_date = None
                
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
    
    # Arelle-specific extraction methods
    def _extract_calculation_arcs_arelle(self, model_xbrl) -> Dict[str, List[CalculationArc]]:
        """使用 Arelle 提取 Calculation Arcs"""
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
    
    def _extract_presentation_arcs_arelle(self, model_xbrl) -> Dict[str, List[PresentationArc]]:
        """使用 Arelle 提取 Presentation Arcs"""
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
    
    def _extract_facts_arelle(self, model_xbrl) -> List[XBRLFact]:
        """使用 Arelle 提取 Facts"""
        facts: List[XBRLFact] = []
        
        try:
            for fact in model_xbrl.facts:
                facts.append(XBRLFact(
                    concept=fact.qname.localName,
                    value=str(fact.value) if fact.value is not None else None,
                    unit=fact.unit.id if fact.unit else None,
                    context_ref=fact.context.id if fact.context else "",
                    decimals=fact.decimals if hasattr(fact, 'decimals') else None,
                ))
        except Exception as e:
            logger.error(f"Error extracting facts with Arelle: {e}")
        
        return facts
    
    def _extract_contexts_arelle(self, model_xbrl) -> Dict[str, XBRLContext]:
        """使用 Arelle 提取 Contexts"""
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
    
    def _extract_labels_arelle(self, model_xbrl) -> tuple[Dict[str, str], Dict[str, str]]:
        """使用 Arelle 提取 Labels"""
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


# Singleton instance
_xbrl_parser: Optional[XBRLParser] = None


def get_xbrl_parser() -> XBRLParser:
    """Get XBRL parser instance (singleton)"""
    global _xbrl_parser
    if _xbrl_parser is None:
        _xbrl_parser = XBRLParser()
    return _xbrl_parser
