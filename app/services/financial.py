"""
Financial Service
Orchestrates MOPS download and XBRL parsing to produce structured financial statements
"""
import logging
from typing import Optional, List
from decimal import Decimal

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
    
    def __init__(self):
        self.mops_client = get_mops_client()
        self.xbrl_parser = get_xbrl_parser()
    
    async def get_financial_statement(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str,
        format: str = "tree",
    ) -> FinancialStatement:
        """
        取得財務報表
        
        Args:
            stock_id: 股票代號
            year: 民國年
            quarter: 季度
            report_type: balance_sheet, income_statement, cash_flow
            format: tree (階層) 或 flat (扁平)
        
        Returns:
            FinancialStatement with hierarchical items
        """
        # 下載 XBRL
        try:
            zip_content = await self.mops_client.download_xbrl(stock_id, year, quarter)
        except MOPSClientError as e:
            raise FinancialServiceError(f"Failed to download XBRL: {e.message}")
        
        # 解析 XBRL
        try:
            package = self.xbrl_parser.parse_zip(zip_content, stock_id, year, quarter)
        except XBRLParserError as e:
            raise FinancialServiceError(f"Failed to parse XBRL: {e}")
        
        # 建構財務報表
        statement = self._build_statement(package, report_type)
        
        # 如果需要扁平格式
        if format == "flat":
            statement.items = self._flatten_items(statement.items)
        
        return statement
    
    def _build_statement(
        self, 
        package: XBRLPackage, 
        report_type: str
    ) -> FinancialStatement:
        """
        從 XBRL Package 建構財務報表
        
        核心邏輯：
        1. 使用 Presentation Linkbase 建立階層結構
        2. 使用 Calculation Linkbase 設定 weight（加減邏輯）
        3. 從 Instance Facts 填入數值
        """
        statement = FinancialStatement(
            stock_id=package.stock_id,
            year=package.year,
            quarter=package.quarter,
            report_type=report_type,
        )
        
        # 建立 concept -> fact value 的映射
        fact_values = {}
        for fact in package.facts:
            fact_values[fact.concept] = fact.value
        
        # 建立 concept -> weight 的映射（從 calculation arcs）
        weight_map = self._build_weight_map(package.calculation_arcs)
        
        # 從 presentation 建立階層結構
        # 找出該報表類型的根節點
        role_key = self.REPORT_ROLES.get(report_type, "")
        
        # 建立樹狀結構
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
                # 記錄每個子節點對其父節點的 weight
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
        """
        從 Presentation Linkbase 建立樹狀結構
        """
        items: List[FinancialItem] = []
        
        # 獲取當前層級的所有項目
        if parent is None:
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
                    value = Decimal(fact_values[concept])
                except (ValueError, TypeError):
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
                account_code=concept,  # 使用 XBRL concept 作為代碼
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
            # 建立不含 children 的副本
            flat_item = item.model_copy()
            flat_item.children = []
            result.append(flat_item)
            
            # 遞迴處理子項目
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
