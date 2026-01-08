# Design v1: Parser Modularization (Full)

## Decision: 採用完整拆解方案

## Proposed Architecture

將 `xbrl_parser.py` 拆分為 `app/parsers/` 模組，每個檔案職責單一。

```
app/
├── services/
│   └── xbrl_parser.py    # [MODIFY] Facade，保留公開 API
│
└── parsers/              # [NEW] 解析模組
    ├── __init__.py       # 匯出解析工具
    ├── arelle.py         # Arelle 解析邏輯
    ├── lxml_parser.py    # lxml 解析邏輯
    ├── linkbase.py       # Linkbase 解析 (calculation, presentation, label)
    └── ixbrl.py          # iXBRL HTML 解析
```

## 模組職責

### `parsers/arelle.py` (~200 行)
```python
class ArelleExtractor:
    """使用 Arelle 提取 XBRL 資料"""
    
    def check_available(self) -> bool
    def load_document(self, path: str) -> ModelXbrl
    def extract_calculation_arcs(self, model_xbrl) -> Dict[str, List[CalculationArc]]
    def extract_presentation_arcs(self, model_xbrl) -> Dict[str, List[PresentationArc]]
    def extract_facts(self, model_xbrl) -> List[XBRLFact]
    def extract_contexts(self, model_xbrl) -> Dict[str, XBRLContext]
    def extract_labels(self, model_xbrl) -> tuple[Dict[str, str], Dict[str, str]]
```

### `parsers/lxml_parser.py` (~150 行)
```python
class LxmlExtractor:
    """使用 lxml 提取 XBRL 資料（Arelle 不可用時的 fallback）"""
    
    def parse_instance_facts(self, content: bytes) -> List[XBRLFact]
    def parse_instance_contexts(self, content: bytes) -> Dict[str, XBRLContext]
```

### `parsers/linkbase.py` (~100 行)
```python
def parse_calculation_linkbase(content: bytes) -> Dict[str, List[CalculationArc]]
def parse_presentation_linkbase(content: bytes) -> Dict[str, List[PresentationArc]]
def parse_label_linkbase(content: bytes) -> tuple[Dict[str, str], Dict[str, str]]
```

### `parsers/ixbrl.py` (~200 行)
```python
class IXBRLParser:
    """解析 Inline XBRL (HTML embedded XBRL)"""
    
    def parse_with_lxml(self, content: bytes) -> tuple[List[XBRLFact], Dict[str, XBRLContext]]
    def extract_labels_from_html(self, content: bytes) -> tuple[Dict[str, str], Dict[str, str]]
    def replace_schema_refs(self, content: bytes) -> bytes
```

### `xbrl_parser.py` (Facade, ~150 行)
```python
class XBRLParser:
    """XBRL 解析器 - Facade Pattern"""
    
    # 公開 API (不變)
    def parse(self, content, stock_id, year, quarter) -> XBRLPackage
    def parse_zip(self, zip_content, stock_id, year, quarter) -> XBRLPackage
    def parse_ixbrl(self, ixbrl_content, stock_id, year, quarter) -> XBRLPackage
    
    # 內部協調 (委派給各模組)
    def _parse_with_arelle(...)
    def _parse_with_lxml(...)
```

## 重構策略：先測試，再重構

### Phase 0: 寫特徵測試 (Characterization Tests)

在重構前，先捕捉目前的行為：

```python
# tests/test_xbrl_parser_behavior.py

class TestXBRLParserBehavior:
    """
    特徵測試：捕捉目前 XBRLParser 的確切行為
    這些測試在重構後必須全部通過
    """
    
    def test_parse_returns_expected_structure(self):
        """測試 parse() 回傳的資料結構"""
        
    def test_calculation_linkbase_weight_extraction(self):
        """測試 weight 屬性正確提取"""
        
    def test_ixbrl_fact_parsing(self):
        """測試 iXBRL fact 解析"""
        
    def test_labels_extraction(self):
        """測試中英文標籤提取"""
```

### Phase 1-4: 拆分模組 (有測試保護)

每拆分一個模組後，執行測試確保行為不變。

## Pros and Cons

### Pros
- ✅ 每個檔案 < 200 行，易於維護
- ✅ 職責單一，符合 SRP
- ✅ 可獨立測試各模組
- ✅ 有完整測試保護
- ✅ 未來擴展容易

### Cons
- ⚠️ 工作量較大
- ⚠️ 需要寫較多測試
- ⚠️ 跨模組依賴需管理
