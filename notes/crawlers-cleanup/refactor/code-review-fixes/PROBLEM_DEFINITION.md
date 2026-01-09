# Code Review Fixes - 問題定義

## 背景

最近實作的額外爬蟲服務 (Revenue, Dividend, Disclosure) 用於擴展財務資料的覆蓋範圍。經過詳細的代碼審查 (`notes/additional-crawlers/feat/CODE_REVIEW.md`)，發現了數個關於代碼重複性、架構設計與錯誤處理的問題。為了確保系統的可維護性與穩定性，需要進行重構。

---

## 現狀分析

### 問題點

1.  **代碼重複 (Code Duplication)**: `RevenueService`, `DividendService`, `DisclosureService` 各自實作了私有的 `_parse_number` 與 `_parse_float` 方法，未利用專案中已存在的 `app/utils/numerics.py`。
2.  **架構違規 (Architectural Violation)**: Pydantic 資料模型 (Schemas) 被定義在 Service 層 (`app/services/*.py`) 中，而非標準的 `app/schemas/` 目錄，違反了關注點分離原則。
3.  **錯誤處理隱晦 (Silent Failures)**: 解析迴圈中使用廣泛的 `except Exception` 並僅紀錄 debug log，這導致解析錯誤難以被察覺，可能造成資料靜默遺失。
4.  **配置分散**: MOPS 的 URL 與參數散落在各個 Service 檔案中，維護困難。

---

## 目標

1.  **統一數值解析**: 重構所有相關 Service 以使用 `app.utils.numerics.parse_financial_value`。
2.  **標準化 Schema 位置**: 將所有 Pydantic Models 移動至 `app/schemas/`。
3.  **優化錯誤處理**: 移除靜默失敗，對非預期的解析錯誤使用 Warning/Error 層級紀錄。
4.  **提升代碼品質**: 清理重複代碼，增強 Type Hints。

---

## 約束

- **API 相容性**: 必須確保重構後的 API 回傳結構維持不變。
- **測試覆蓋**: 雖然會修改代碼結構，但業務邏輯應保持一致，需確保現有測試 (修正 import 後) 通過。

---

## 範圍

| 包含 | 不包含 |
|------|--------|
| `app/services/revenue.py` 重構 | 資料庫 Schema 變更 |
| `app/services/dividend.py` 重構 | 新增爬蟲功能 |
| `app/services/disclosure.py` 重構 | 全面性的 `MOPSClient` 重寫 (僅做 URL 管理的初步優化) |
| 新增 `app/schemas/{revenue,dividend,disclosure}.py` | |
