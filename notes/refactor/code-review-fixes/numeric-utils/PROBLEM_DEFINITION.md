# Problem Definition: Numeric Utils Refactoring

## Background

在 `CODE_REVIEW.md` 中發現的 **Critical** 問題：數值解析邏輯重複且脆弱。

字串轉數值（移除逗號、處理小數點、處理空值）的邏輯被複製貼上在多個地方。
任何修改都需要同步更新所有位置，極易出錯。

## Current State

以下位置存在重複的數值清理邏輯 `str.replace(",", "").strip()`：

| 檔案 | 行號 | 用途 |
|------|------|------|
| `app/services/xbrl_parser.py` | L196 | iXBRL 解析時移除逗號 |
| `app/services/financial.py` | L175-176 | Q4 單季計算 (q4_clean, q3_clean) |
| `app/services/financial.py` | L298 | Fallback items 解析 |
| `app/services/financial.py` | L353 | 樹狀結構解析 |
| `app/routers/financial.py` | L206 | Simplified API 數值轉換 |

## Pain Points

1. **DRY 違規**: 同樣的邏輯複製 5+ 次
2. **一致性風險**: 修改時容易漏改某處
3. **邊界條件處理不一致**:
   - 有些地方用 `isdigit()`
   - 有些地方用 `lstrip('-').replace('.', '').isdigit()`
   - 有些地方直接 try/except
4. **測試困難**: 無法單獨測試數值解析邏輯

## Goals

1. 建立統一的 `app/utils/numerics.py` 模組
2. 提供 `parse_financial_value(value_str: str) -> Optional[Decimal]` 函式
3. 統一處理：
   - 逗號移除
   - 空白清理
   - 空值/破折號處理
   - 數值驗證
4. 提供單元測試覆蓋各種邊界條件

## Constraints

- 必須保持後向相容，不改變 API 回傳格式
- 解析結果必須與目前行為一致（先通過既有測試）
- 使用 `Decimal` 而非 `float` 以保持精度
