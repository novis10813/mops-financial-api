# Impact Analysis: Parser Modularization

## Files to be Created

| File | Purpose | Est. Lines |
|------|---------|------------|
| `app/parsers/__init__.py` | 匯出解析工具 | ~20 |
| `app/parsers/arelle.py` | Arelle 解析邏輯 | ~200 |
| `app/parsers/lxml_parser.py` | lxml 解析邏輯 | ~150 |
| `app/parsers/linkbase.py` | Linkbase 解析 | ~100 |
| `app/parsers/ixbrl.py` | iXBRL HTML 解析 | ~200 |
| `tests/test_xbrl_parser_behavior.py` | 特徵測試 | ~150 |

## Files to be Modified

| File | Changes |
|------|---------|
| `app/services/xbrl_parser.py` | 從 858 行減至 ~150 行，成為 Facade |

## Files that May be Deleted

無

## Dependencies Between Components

```
xbrl_parser.py (Facade)
    ├── parsers/arelle.py      (Arelle available)
    ├── parsers/lxml_parser.py (Arelle fallback)
    ├── parsers/linkbase.py    (共用)
    └── parsers/ixbrl.py       (iXBRL format)
```

## 方法對應表

| 原方法 | 目標模組 |
|--------|----------|
| `_check_arelle()` | `arelle.py` |
| `_parse_with_arelle()` | `arelle.py` |
| `_parse_ixbrl_with_arelle()` | `arelle.py` + `ixbrl.py` |
| `_extract_calculation_arcs_arelle()` | `arelle.py` |
| `_extract_presentation_arcs_arelle()` | `arelle.py` |
| `_extract_facts_arelle()` | `arelle.py` |
| `_extract_contexts_arelle()` | `arelle.py` |
| `_extract_labels_arelle()` | `arelle.py` |
| `_parse_with_lxml()` | `lxml_parser.py` |
| `_parse_instance_facts()` | `lxml_parser.py` |
| `_parse_instance_contexts()` | `lxml_parser.py` |
| `_parse_calculation_linkbase()` | `linkbase.py` |
| `_parse_presentation_linkbase()` | `linkbase.py` |
| `_parse_label_linkbase()` | `linkbase.py` |
| `_replace_schema_refs()` | `ixbrl.py` |
| `_extract_labels_from_html()` | `ixbrl.py` |
| iXBRL lxml 解析 (L167-268) | `ixbrl.py` |

## Potential Breaking Changes

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Import 路徑變更 | 無 | 保持 `from app.services.xbrl_parser import` 不變 |
| 行為差異 | 低 | 特徵測試確保一致性 |
| Arelle 整合問題 | 中 | 保留 fallback 邏輯 |

## Risks and Edge Cases

1. **Arelle ModelXbrl 物件**: 需確保跨模組傳遞正確
2. **Schema ref 路徑**: 本地 taxonomy 路徑邏輯需保持一致
3. **錯誤處理**: 異常應正確傳播到 Facade
