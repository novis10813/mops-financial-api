# Problem Definition: Parser Modularization

## Background

在 `CODE_REVIEW.md` 中發現的 **Medium** 問題：`xbrl_parser.py` 職責過重。

該檔案目前有 **858 行**，同時包含：
- ZIP 解壓邏輯
- iXBRL HTML 解析 (lxml)
- XBRL 解析 (Arelle)
- Taxonomy Linkbase 解析 (Calculation, Presentation, Label)
- Schema ref 替換邏輯
- HTML Label 提取

## Current State

### 方法分類

| 類別 | 方法 | 行數 |
|------|------|------|
| **入口點** | `parse()`, `parse_zip()`, `parse_ixbrl()` | ~150 |
| **Arelle 解析** | `_parse_with_arelle()`, `_parse_ixbrl_with_arelle()`, `_extract_*_arelle()` | ~200 |
| **lxml 解析** | `_parse_with_lxml()`, `_parse_instance_*()` | ~120 |
| **Linkbase 解析** | `_parse_calculation_linkbase()`, `_parse_presentation_linkbase()`, `_parse_label_linkbase()` | ~90 |
| **輔助方法** | `_find_instance_file()`, `_replace_schema_refs()`, `_extract_labels_from_html()` | ~150 |
| **其他** | Imports, constants, singleton | ~150 |

## Pain Points

1. **檔案過大**: 858 行難以維護和理解
2. **職責混雜**: 混合了多種解析策略 (Arelle vs lxml)
3. **測試困難**: 難以單獨測試某個解析邏輯
4. **擴展困難**: 新增解析策略需修改這個大檔案

## Goals

1. 將 `xbrl_parser.py` 拆分為多個模組
2. 每個模組職責單一
3. 保持現有 API 不變（`XBRLParser` class 和 `get_xbrl_parser()`）
4. 提高可測試性

## Constraints

- 不改變 `XBRLParser` 的公開 API
- 保持與 Arelle 和 lxml 的相容性
- 現有測試必須通過
