# Changelog: parser-modularization

## [Unreleased] - 2026-01-08

### Added
- `app/parsers/` 模組套件
  - `__init__.py` - 匯出所有解析工具
  - `linkbase.py` - Calculation/Presentation/Label Linkbase 解析
  - `lxml_parser.py` - lxml-based instance parsing (fallback)
  - `arelle.py` - Arelle extraction functions
  - `ixbrl.py` - iXBRL utilities (schema ref, labels)
- `tests/test_xbrl_parser_behavior.py` - 15 個特徵測試

### Changed
- `app/services/xbrl_parser.py`
  - 從 858 行減至 530 行 (減少 38%)
  - 委派所有解析邏輯給 `app.parsers.*` 模組
  - 保留 Facade pattern 和公開 API

### Fixed
- 消除 `xbrl_parser.py` 職責過重問題 (CODE_REVIEW Medium Issue)

### Technical Notes
- 所有 45 個測試通過，行為不變
- 公開 API (`XBRLParser`, `get_xbrl_parser()`) 完全相容

### Module Structure
```
app/parsers/         新增 626 行
├── __init__.py         53 行
├── linkbase.py        142 行
├── lxml_parser.py     108 行
├── arelle.py          176 行
└── ixbrl.py           147 行
```
