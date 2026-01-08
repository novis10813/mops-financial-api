"""
XBRL Parsers Package

提供模組化的 XBRL 解析工具
"""
# Linkbase parsing
from app.parsers.linkbase import (
    parse_calculation_linkbase,
    parse_presentation_linkbase,
    parse_label_linkbase,
)

# lxml-based parsing (fallback)
from app.parsers.lxml_parser import (
    parse_instance_facts,
    parse_instance_contexts,
)

# Arelle-based parsing (full functionality)
from app.parsers.arelle import (
    check_arelle_available,
    extract_calculation_arcs,
    extract_presentation_arcs,
    extract_facts,
    extract_contexts,
    extract_labels,
)

# iXBRL utilities
from app.parsers.ixbrl import (
    replace_schema_refs,
    extract_labels_from_html,
)

__all__ = [
    # Linkbase
    "parse_calculation_linkbase",
    "parse_presentation_linkbase",
    "parse_label_linkbase",
    # lxml
    "parse_instance_facts",
    "parse_instance_contexts",
    # Arelle
    "check_arelle_available",
    "extract_calculation_arcs",
    "extract_presentation_arcs",
    "extract_facts",
    "extract_contexts",
    "extract_labels",
    # iXBRL
    "replace_schema_refs",
    "extract_labels_from_html",
]
