"""
Financial Service
Orchestrates MOPS download and XBRL parsing to produce structured financial statements

Key Feature: Q4 Standalone Calculation
- For income statement: Q4 standalone = Annual - Q3 accumulated
- For balance sheet & cash flow: No calculation needed
"""
import logging
from typing import Optional, List, Dict
from decimal import Decimal, InvalidOperation

from app.schemas.financial import FinancialStatement, FinancialItem
from app.schemas.xbrl import XBRLPackage, CalculationArc
from app.services.mops_client import get_mops_client, MOPSClientError
from app.services.xbrl_parser import get_xbrl_parser, XBRLParserError

logger = logging.getLogger(__name__)


class FinancialServiceError(Exception):
    """Financial Service Error"""
    pass


class FinancialService:
    """
    財務報表服務
    整合 MOPS 下載與 XBRL 解析，產出結構化財務報表
    """
    
    # 報表類型對應的 XBRL Role
    REPORT_ROLES = {
        "balance_sheet": "StatementOfFinancialPosition",
        "income_statement": "StatementOfComprehensiveIncome",
        "cash_flow": "StatementOfCashFlows",
    }
    
    # 需要計算 Q4 單季的報表類型
    CUMULATIVE_REPORTS = {"income_statement"}  # 損益表是累計的
    
    def __init__(self):
        self.mops_client = get_mops_client()
        self.xbrl_parser = get_xbrl_parser()
    
    async def get_financial_statement(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        report_type: str = "balance_sheet",
        format: str = "tree",
    ) -> FinancialStatement:
        """
        取得財務報表
        
        Args:
            stock_id: 股票代號
            year: 民國年
            quarter: 季度 (1-4)，若為 None 則取年報原始資料
            report_type: balance_sheet, income_statement, cash_flow
            format: tree (階層) 或 flat (扁平)
        
        Returns:
            FinancialStatement with hierarchical items
        
        Note:
            - quarter=4 時，損益表會計算 Q4 單季 = 年報 - Q3累計
            - quarter=None 時，直接回傳年報（Q4）原始資料
        """
        # 決定要下載的季度
        download_quarter = quarter if quarter else 4
        
        # 下載 XBRL
        try:
            content = await self.mops_client.download_xbrl(stock_id, year, download_quarter)
        except MOPSClientError as e:
            raise FinancialServiceError(f"Failed to download XBRL: {e.message}")
        
        # 解析 XBRL
        try:
            # 判斷是 ZIP 還是 iXBRL
            package = self.xbrl_parser.parse(content, stock_id, year, download_quarter)
        except XBRLParserError as e:
            raise FinancialServiceError(f"Failed to parse XBRL: {e}")
        
        # Q4 單季計算：只有指定 quarter=4 且是累計型報表才需要
        if quarter == 4 and report_type in self.CUMULATIVE_REPORTS:
            statement = await self._get_q4_standalone(
                stock_id, year, report_type, package, format
            )
        else:
            # 一般情況：直接建構報表
            statement = self._build_statement(package, report_type)
        
        # 如果需要扁平格式
        if format == "flat":
            statement.items = self._flatten_items(statement.items)
        
        return statement
    
    async def _get_q4_standalone(
        self,
        stock_id: str,
        year: int,
        report_type: str,
        q4_package: XBRLPackage,
        format: str,
    ) -> FinancialStatement:
        """
        計算 Q4 單季數據
        
        Q4 單季 = 年報(Q4) - Q3 累計
        """
        logger.info(f"Calculating Q4 standalone for {stock_id} {year}")
        
        # 下載 Q3 資料
        try:
            q3_content = await self.mops_client.download_xbrl(stock_id, year, 3)
            q3_package = self.xbrl_parser.parse(q3_content, stock_id, year, 3)
        except (MOPSClientError, XBRLParserError) as e:
            logger.warning(f"Failed to get Q3 data, returning Q4 as-is: {e}")
            return self._build_statement(q4_package, report_type)
        
        # 建立 Q4 和 Q3 的 fact 映射
        q4_facts = {fact.concept: fact.value for fact in q4_package.facts}
        q3_facts = {fact.concept: fact.value for fact in q3_package.facts}
        
        # 計算差值
        q4_standalone_facts = {}
        for concept, q4_value in q4_facts.items():
            q3_value = q3_facts.get(concept, "0")
            
            try:
                # 清理數值字串
                q4_clean = str(q4_value).replace(",", "").strip() if q4_value else ""
                q3_clean = str(q3_value).replace(",", "").strip() if q3_value else ""
                
                # 跳過空值或非數值
                if not q4_clean or not q4_clean.lstrip('-').replace('.', '').isdigit():
                    q4_standalone_facts[concept] = q4_value
                    continue
                
                q4_num = Decimal(q4_clean)
                q3_num = Decimal(q3_clean) if q3_clean and q3_clean.lstrip('-').replace('.', '').isdigit() else Decimal(0)
                q4_standalone_facts[concept] = str(q4_num - q3_num)
            except Exception:
                # 非數值型資料，保留原值
                q4_standalone_facts[concept] = q4_value
        
        # 用計算後的 facts 建立報表
        statement = self._build_statement_with_facts(
            q4_package, report_type, q4_standalone_facts
        )
        statement.quarter = 4
        statement.is_standalone = True  # 標記為單季資料
        
        return statement
    
    def _build_statement(
        self, 
        package: XBRLPackage, 
        report_type: str
    ) -> FinancialStatement:
        """從 XBRL Package 建構財務報表"""
        fact_values = {fact.concept: fact.value for fact in package.facts}
        return self._build_statement_with_facts(package, report_type, fact_values)
    
    def _build_statement_with_facts(
        self,
        package: XBRLPackage,
        report_type: str,
        fact_values: Dict[str, str],
    ) -> FinancialStatement:
        """
        從 XBRL Package 和自訂 fact values 建構財務報表
        
        核心邏輯：
        1. 使用 Presentation Linkbase 建立階層結構
        2. 使用 Calculation Linkbase 設定 weight（加減邏輯）
        3. 從提供的 fact_values 填入數值
        """
        statement = FinancialStatement(
            stock_id=package.stock_id,
            year=package.year,
            quarter=package.quarter,
            report_type=report_type,
        )
        
        # 建立 concept -> weight 的映射（從 calculation arcs）
        weight_map = self._build_weight_map(package.calculation_arcs)
        
        # 從 presentation 建立階層結構
        items = self._build_tree_from_presentation(
            package.presentation_arcs,
            package.labels,
            package.labels_en,
            fact_values,
            weight_map,
        )
        
        statement.items = items
        return statement
    
    def _build_weight_map(
        self, 
        calculation_arcs: dict[str, list[CalculationArc]]
    ) -> dict[str, float]:
        """
        建立 concept -> weight 的映射
        
        這是解決「加減邏輯」的核心：
        weight = 1.0 表示該項目加到父節點
        weight = -1.0 表示該項目從父節點減去
        """
        weight_map: dict[str, float] = {}
        
        for parent, arcs in calculation_arcs.items():
            for arc in arcs:
                weight_map[arc.to_concept] = arc.weight
        
        return weight_map
    
    def _build_tree_from_presentation(
        self,
        presentation_arcs: dict[str, list],
        labels_zh: dict[str, str],
        labels_en: dict[str, str],
        fact_values: dict[str, str],
        weight_map: dict[str, float],
        parent: Optional[str] = None,
        level: int = 0,
    ) -> List[FinancialItem]:
        """從 Presentation Linkbase 建立樹狀結構"""
        items: List[FinancialItem] = []
        
        # 獲取當前層級的所有項目
        if parent is None:
            # 根節點處理
            if not presentation_arcs:
                # Fallback: 如果沒有 presentation linkbase (e.g. iXBRL parsing without schema),
                # 直接回傳所有有值的 facts 作為平鋪列表
                logger.warning("No presentation arcs found, falling back to all facts list")
                fallback_items = []
                for concept, value_str in fact_values.items():
                    # 解析數值
                    value = None
                    try:
                        clean_val = str(value_str).replace(",", "").strip()
                        if clean_val and (clean_val.isdigit() or clean_val.lstrip('-').replace('.', '').isdigit()):
                            value = Decimal(clean_val)
                    except (ValueError, TypeError):
                        pass

                    label_zh = labels_zh.get(concept, concept)
                    label_en = labels_en.get(concept)
                    
                    fallback_items.append(FinancialItem(
                        account_code=concept,
                        account_name=label_zh,
                        account_name_en=label_en,
                        value=value,
                        weight=1.0,
                        level=0,
                        children=[]
                    ))
                # 簡單排序
                fallback_items.sort(key=lambda x: x.account_code)
                return fallback_items

            # 根節點：找出沒有被其他節點參照的概念
            all_children = set()
            for arcs in presentation_arcs.values():
                for arc in arcs:
                    all_children.add(arc.to_concept)
            
            root_concepts = set(presentation_arcs.keys()) - all_children
            current_arcs = [
                type('Arc', (), {'to_concept': c, 'order': 0})()
                for c in sorted(root_concepts)
            ]
        else:
            current_arcs = presentation_arcs.get(parent, [])
        
        # 按 order 排序
        sorted_arcs = sorted(current_arcs, key=lambda x: x.order)
        
        for arc in sorted_arcs:
            concept = arc.to_concept
            
            # 取得標籤
            label_zh = labels_zh.get(concept, concept)
            label_en = labels_en.get(concept)
            
            # 取得數值
            value = None
            if concept in fact_values and fact_values[concept]:
                try:
                    val_str = str(fact_values[concept]).replace(",", "").strip()
                    if val_str and val_str not in ("-", ""):
                        value = Decimal(val_str)
                except (ValueError, TypeError, InvalidOperation):
                    pass
            
            # 取得 weight（加減邏輯）
            weight = weight_map.get(concept, 1.0)
            
            # 遞迴建立子項目
            children = self._build_tree_from_presentation(
                presentation_arcs,
                labels_zh,
                labels_en,
                fact_values,
                weight_map,
                parent=concept,
                level=level + 1,
            )
            
            item = FinancialItem(
                account_code=concept,
                account_name=label_zh,
                account_name_en=label_en,
                value=value,
                weight=weight,
                level=level,
                children=children,
            )
            
            items.append(item)
        
        return items
    
    def _flatten_items(
        self, 
        items: List[FinancialItem], 
        result: Optional[List[FinancialItem]] = None
    ) -> List[FinancialItem]:
        """將階層結構扁平化"""
        if result is None:
            result = []
        
        for item in items:
            flat_item = item.model_copy()
            flat_item.children = []
            result.append(flat_item)
            
            if item.children:
                self._flatten_items(item.children, result)
        
        return result


# Singleton instance
_financial_service: Optional[FinancialService] = None


def get_financial_service() -> FinancialService:
    """Get financial service instance (singleton)"""
    global _financial_service
    if _financial_service is None:
        _financial_service = FinancialService()
    return _financial_service
