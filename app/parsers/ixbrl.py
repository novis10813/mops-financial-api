"""
iXBRL (Inline XBRL) 解析輔助模組

提供 iXBRL 解析所需的輔助功能：
- Schema ref 路徑替換
- HTML 標籤提取
"""
import io
import logging
from pathlib import Path
from typing import Dict, Tuple

from lxml import etree

logger = logging.getLogger(__name__)


def replace_schema_refs(content: bytes, schema_mappings: Dict[str, str]) -> bytes:
    """
    將 iXBRL 中的相對 schemaRef 路徑替換為本地 taxonomy 路徑
    
    例如：
    xlink:href="tifrs-ci-cr-2020-06-30.xsd"
    -> xlink:href="file:///path/to/taxonomy/.../tifrs-ci-cr-2020-06-30.xsd"
    
    Args:
        content: iXBRL HTML bytes
        schema_mappings: {relative_schema: local_path} 映射
        
    Returns:
        替換後的 bytes
    """
    try:
        content_str = content.decode('utf-8')
        
        for relative_schema, local_path in schema_mappings.items():
            full_local_path = Path(local_path)
            if full_local_path.exists():
                # 替換相對路徑為 file:// URI
                old_ref = f'xlink:href="{relative_schema}"'
                new_ref = f'xlink:href="file://{full_local_path}"'
                if old_ref in content_str:
                    content_str = content_str.replace(old_ref, new_ref)
                    logger.info(f"Replaced schema ref: {relative_schema} -> {full_local_path}")
                    break
        
        return content_str.encode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to replace schema refs: {e}")
        return content


def extract_labels_from_html(content: bytes) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    從 iXBRL HTML 結構中提取標籤
    
    Taiwan IFRS 的 iXBRL 文件中，數值通常在表格中顯示，
    同一行會有中英文標籤。這個方法透過遍歷 ix:nonFraction 元素
    並找到其父表格行來提取標籤。
    
    Args:
        content: iXBRL HTML bytes
        
    Returns:
        (labels_zh, labels_en) 兩個字典，key 為 concept name
    """
    labels_zh: Dict[str, str] = {}
    labels_en: Dict[str, str] = {}
    
    try:
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.parse(io.BytesIO(content), parser)
        root = tree.getroot()
        
        for elem in root.iter():
            tag_lower = str(elem.tag).lower()
            if 'nonfraction' not in tag_lower:
                continue
            
            name = elem.get("name", "")
            if not name:
                continue
            
            concept = name.split(":")[-1] if ":" in name else name
            
            # 如果已經有這個 concept 的標籤，跳過
            if concept in labels_zh:
                continue
            
            # 向上查找父表格行 (tr)
            parent = elem.getparent()
            row = None
            for _ in range(15):  # 最多向上 15 層
                if parent is None:
                    break
                if parent.tag and 'tr' in str(parent.tag).lower():
                    row = parent
                    break
                parent = parent.getparent()
            
            if row is None:
                continue
            
            # 在行中查找第一個有意義文字的單元格（通常是標籤）
            for cell in row.iter():
                cell_tag = str(cell.tag).lower() if cell.tag else ""
                if 'td' not in cell_tag and 'th' not in cell_tag:
                    continue
                
                # 提取所有文字內容
                text = ''.join(cell.itertext()).strip()
                if not text:
                    continue
                
                # 跳過純數字內容
                clean_text = text.replace(',', '').replace('-', '').replace('.', '').replace(' ', '')
                if clean_text.isdigit():
                    continue
                
                # 分離中英文標籤（Taiwan IFRS 常用全形空格或兩個半形空格分隔）
                # 例如: "現金及約當現金　　Cash and cash equivalents"
                parts = text.split('\u3000\u3000')  # 全形空格
                if len(parts) < 2:
                    parts = text.split('  ')  # 兩個半形空格
                
                if len(parts) >= 2:
                    zh_text = parts[0].strip()
                    en_text = parts[1].strip()[:100]  # 限制長度
                    if zh_text:
                        labels_zh[concept] = zh_text
                    if en_text:
                        labels_en[concept] = en_text
                else:
                    # 只有單一標籤，判斷是中文還是英文
                    if any('\u4e00' <= c <= '\u9fff' for c in text):
                        labels_zh[concept] = text[:100]
                    else:
                        labels_en[concept] = text[:100]
                
                break  # 找到第一個有效標籤就停止
        
        logger.info(f"Extracted {len(labels_zh)} Chinese labels and {len(labels_en)} English labels from HTML")
        
    except Exception as e:
        logger.error(f"Error extracting labels from HTML: {e}")
    
    return labels_zh, labels_en
