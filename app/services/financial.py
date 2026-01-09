"""
Financial Service
Orchestrates MOPS download and XBRL parsing to produce structured financial statements

Caching Strategy:
- Check database cache first before fetching from MOPS
- Save fetched reports to database for future requests
"""
import logging
from typing import Optional, List, Dict


from app.schemas.financial import FinancialStatement, FinancialItem
from app.schemas.xbrl import XBRLPackage, CalculationArc
from app.services.mops_client import get_mops_client, MOPSClientError
from app.services.xbrl_parser import get_xbrl_parser, XBRLParserError
from app.utils.numerics import parse_financial_value
from app.db.connection import get_session
from app.db.repository import FinancialRepository

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
        "equity_statement": "StatementOfChangesInEquity",
    }
    

    
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
        use_cache: bool = True,
    ) -> FinancialStatement:
        """
        取得財務報表（優先從資料庫快取讀取）
        
        Args:
            stock_id: 股票代號
            year: 民國年
            quarter: 季度 (1-4)，若為 None 則取年報原始資料
            report_type: balance_sheet, income_statement, cash_flow
            format: tree (階層) 或 flat (扁平)
            use_cache: 是否使用資料庫快取（預設 True）
        
        Returns:
            FinancialStatement with hierarchical items
        
        Note:
            - quarter=4 時，損益表會計算 Q4 單季 = 年報 - Q3累計
            - quarter=None 時，直接回傳年報（Q4）原始資料
            - 快取以 (stock_id, year, quarter, report_type) 為 key
        """
        # 決定要下載的季度
        download_quarter = quarter if quarter else 4
        
        # 1. 先檢查資料庫快取
        if use_cache:
            try:
                async with get_session() as session:
                    repo = FinancialRepository(session)
                    cached = await repo.get_report(
                        stock_id=stock_id,
                        year=year,
                        quarter=download_quarter,
                        report_type=report_type,
                    )
                    if cached:
                        logger.info(f"Cache hit for {stock_id} {year}Q{download_quarter} {report_type}")
                        # 如果需要扁平格式
                        if format == "flat":
                            cached.items = self._flatten_items(cached.items)
                        return cached
            except Exception as e:
                logger.warning(f"Cache lookup failed, falling back to MOPS: {e}")
        
        # 2. 沒有快取，從 MOPS 下載
        logger.info(f"Cache miss for {stock_id} {year}Q{download_quarter} {report_type}, fetching from MOPS")
        
        try:
            content = await self.mops_client.download_xbrl(stock_id, year, download_quarter)
        except MOPSClientError as e:
            raise FinancialServiceError(f"Failed to download XBRL: {e.message}")
        
        # 解析 XBRL
        try:
            package = self.xbrl_parser.parse(content, stock_id, year, download_quarter)
        except XBRLParserError as e:
            raise FinancialServiceError(f"Failed to parse XBRL: {e}")
        
        # 直接建構報表
        statement = self._build_statement(package, report_type)
        
        # 3. 儲存到資料庫快取
        try:
            async with get_session() as session:
                repo = FinancialRepository(session)
                await repo.save_report(statement)
                logger.info(f"Saved to cache: {stock_id} {year}Q{download_quarter} {report_type}")
        except Exception as e:
            logger.warning(f"Failed to save to cache (non-fatal): {e}")
        
        # 如果需要扁平格式
        if format == "flat":
            statement.items = self._flatten_items(statement.items)
        
        return statement
    
    async def get_simplified_statement(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        statement_type: str = "income_statement",
    ) -> "SimplifiedFinancialStatement":
        """
        取得 FinMind 風格的扁平化財報
        
        Args:
            stock_id: 股票代號
            year: 民國年
            quarter: 季度 (1-4)，若為 None 則取 Q4
            statement_type: 報表類型 (income_statement, balance_sheet, cash_flow)
        
        Returns:
            SimplifiedFinancialStatement
        """
        q = quarter or 4
        
        try:
            content = await self.mops_client.download_xbrl(stock_id, year, q)
        except MOPSClientError as e:
            raise FinancialServiceError(f"Failed to download XBRL: {e.message}")
        
        try:
            package = self.xbrl_parser.parse(content, stock_id, year, q)
        except XBRLParserError as e:
            raise FinancialServiceError(f"Failed to parse XBRL: {e}")
        
        return self._convert_to_simplified(package, stock_id, year, q, statement_type)
    
    def _convert_to_simplified(
        self,
        package: XBRLPackage,
        stock_id: str,
        year: int,
        quarter: int,
        statement_type: str,
    ) -> "SimplifiedFinancialStatement":
        """
        將 XBRLPackage 轉換為 SimplifiedFinancialStatement
        
        Args:
            package: 解析後的 XBRL 資料
            stock_id: 股票代號
            year: 民國年
            quarter: 季度
            statement_type: 報表類型
        
        Returns:
            SimplifiedFinancialStatement
        """
        from app.schemas.simplified import SimplifiedFinancialStatement, SimplifiedFinancialItem
        
        # 計算報表日期 (西元年)
        western_year = year + 1911
        quarter_month = {1: "03", 2: "06", 3: "09", 4: "12"}
        quarter_day = {1: "31", 2: "30", 3: "30", 4: "31"}
        report_date = f"{western_year}-{quarter_month[quarter]}-{quarter_day[quarter]}"
        
        # 轉換 facts 為 FinMind 格式
        simplified_items = []
        seen_types: set = set()
        
        for fact in package.facts:
            concept = fact.concept
            if concept in seen_types:
                continue
            
            if fact.value is None:
                continue
            
            parsed = parse_financial_value(fact.value)
            if parsed is None:
                continue
            
            seen_types.add(concept)
            origin_name = package.labels.get(concept, concept)
            
            simplified_items.append(SimplifiedFinancialItem(
                date=report_date,
                stock_id=stock_id,
                type=concept,
                value=float(parsed),
                origin_name=origin_name
            ))
        
        return SimplifiedFinancialStatement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_date=report_date,
            statement_type=statement_type,
            items=simplified_items
        )
    
    
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
        visited: Optional[set] = None,
        max_depth: int = 20,
    ) -> List[FinancialItem]:
        """從 Presentation Linkbase 建立樹狀結構"""
        items: List[FinancialItem] = []
        
        # 初始化 visited set
        if visited is None:
            visited = set()
        
        # 防止無限遞迴：最大深度或已訪問過
        if level > max_depth:
            return items
        
        # 獲取當前層級的所有項目
        if parent is None:
            # 根節點處理
            if not presentation_arcs:
                # Fallback: 如果沒有 presentation linkbase (e.g. iXBRL parsing without schema),
                # 直接回傳所有有值的 facts 作為平鋪列表
                logger.warning("No presentation arcs found, falling back to all facts list")
                fallback_items = []
                for concept, value_str in fact_values.items():
                    # 解析數值（使用統一工具）
                    value = parse_financial_value(value_str)

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
            
            # 跳過已訪問過的節點（防止循環引用）
            if concept in visited:
                continue
            visited.add(concept)
            
            # 取得標籤
            label_zh = labels_zh.get(concept, concept)
            label_en = labels_en.get(concept)
            
            # 取得數值（使用統一工具）
            value = parse_financial_value(fact_values.get(concept))
            
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
                visited=visited,
                max_depth=max_depth,
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
