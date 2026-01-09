# 代碼審查: feat/equity-statement

## 1. 變更摘要
新增「權益變動表」(Statement of Changes in Equity) 的支援，包含 Service 層的設定 (XBRL Role 與累計屬性) 以及 Router 層的 API 端點實作。

## 2. 重點發現 (Key Findings)

無重大問題發現。代碼結構清晰，且完整依循現有架構擴充。

### 🚨 Critical
- 無

### ⚠️ High
- 無

### 💡 Medium
- 無

### ℹ️ Low
- 無

## 3. 安全與合規檢查 (Security & Compliance)
- 敏感資訊:✅ 無硬編碼敏感資訊。
- 漏洞掃描:✅ 輸入參數由 FastAPI 進行型別與範圍驗證 (e.g., `quarter` 限制 1-4)，無明顯注入風險。

## 4. 代碼品質評分 (Quality Score)
- **可讀性**: 10/10
- **測試覆蓋建議**: 建議補上針對 `get_equity_statement` 的整合測試，特別是 Q4 自動計算邏輯的驗證。
- **複雜度**: 低。直接調用 Service 層邏輯。

## 5. 詳細建議 (Actionable Recommendations)

代碼實作正確且符合設計文件，無需修改。

建議在合併後，確認以下測試案例：
1. 查詢 Q1-Q3 權益變動表，確認數值正確。
2. 查詢 Q4 權益變動表，確認系統有正確執行 `年報 - Q3累計` 的單季計算邏輯。
