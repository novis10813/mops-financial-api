# 權益變動表 (Statement of Changes in Equity) 抓取功能

## 功能描述

新增權益變動表 (Statement of Changes in Equity) 端點，完成四大財務報表的支援：
1. ✅ 資產負債表 (Balance Sheet)
2. ✅ 綜合損益表 (Income Statement)
3. ✅ 現金流量表 (Cash Flow)
4. ⬜ **權益變動表 (Changes in Equity)** ← 新增

## 使用場景

1. 投資人分析公司股東權益變動來源
2. 了解保留盈餘、股利發放、增資減資等權益項目
3. 配合其他三表做全面性財務分析

## 驗收條件

- [ ] 新增 `GET /financial/{stock_id}/equity-statement` 端點
- [ ] 支援 `year` 和 `quarter` 參數
- [ ] 支援 `tree` / `flat` 輸出格式
- [ ] 支援資料庫快取
- [ ] 支援 Q4 單季計算（累計型報表）
- [ ] 現有測試通過

## 技術備註

- XBRL Role: `StatementOfChangesInEquity`
- 權益變動表為**累計型**報表，需加入 `CUMULATIVE_REPORTS`
