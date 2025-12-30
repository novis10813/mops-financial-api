"""
XBRL-related schemas
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CalculationArc(BaseModel):
    """XBRL Calculation Arc - 定義運算邏輯"""
    from_concept: str = Field(..., description="父節點概念 ID")
    to_concept: str = Field(..., description="子節點概念 ID")
    weight: float = Field(..., description="權重 (+1.0 加 / -1.0 減)")
    order: float = Field(0.0, description="排序順序")


class PresentationArc(BaseModel):
    """XBRL Presentation Arc - 定義展示階層"""
    from_concept: str = Field(..., description="父節點概念 ID")
    to_concept: str = Field(..., description="子節點概念 ID")
    order: float = Field(0.0, description="排序順序")
    preferred_label: Optional[str] = Field(None, description="偏好標籤")


class XBRLFact(BaseModel):
    """XBRL Fact - 單一數值"""
    concept: str = Field(..., description="概念 ID")
    value: Optional[str] = Field(None, description="數值（字串形式）")
    unit: Optional[str] = Field(None, description="單位")
    context_ref: str = Field(..., description="Context 參照")
    decimals: Optional[int] = Field(None, description="小數位數")


class XBRLContext(BaseModel):
    """XBRL Context - 報告情境"""
    context_id: str = Field(..., description="Context ID")
    entity: str = Field(..., description="報告實體（公司代號）")
    period_start: Optional[str] = Field(None, description="期間開始日期")
    period_end: Optional[str] = Field(None, description="期間結束日期")
    instant: Optional[str] = Field(None, description="時點日期")


class XBRLPackage(BaseModel):
    """解析後的 XBRL 套件"""
    stock_id: str
    year: int
    quarter: int
    
    # Linkbase 內容
    calculation_arcs: Dict[str, List[CalculationArc]] = Field(
        default_factory=dict, 
        description="Calculation Linkbase: {parent -> [arcs]}"
    )
    presentation_arcs: Dict[str, List[PresentationArc]] = Field(
        default_factory=dict,
        description="Presentation Linkbase: {parent -> [arcs]}"
    )
    
    # Instance 內容
    facts: List[XBRLFact] = Field(default_factory=list, description="數值資料")
    contexts: Dict[str, XBRLContext] = Field(default_factory=dict, description="Context 定義")
    
    # Labels
    labels: Dict[str, str] = Field(default_factory=dict, description="概念 -> 中文標籤")
    labels_en: Dict[str, str] = Field(default_factory=dict, description="概念 -> 英文標籤")


class XBRLDownloadResponse(BaseModel):
    """XBRL 下載回應"""
    stock_id: str
    year: int
    quarter: int
    filename: str
    size_bytes: int
    download_url: Optional[str] = None
