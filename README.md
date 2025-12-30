# MOPS Financial API

財務報表 XBRL 解析 REST API 服務

## 功能

- 從公開資訊觀測站 (MOPS) 下載 XBRL 財報檔案
- 使用 Arelle 解析 XBRL Calculation Linkbase 取得運算邏輯
- 提供階層化財務報表 API

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/financial/{stock_id}/balance-sheet` | 資產負債表 |
| `GET /api/v1/financial/{stock_id}/income-statement` | 綜合損益表 |
| `GET /api/v1/financial/{stock_id}/cash-flow` | 現金流量表 |
| `GET /api/v1/xbrl/{stock_id}/download` | 下載原始 XBRL ZIP |

## Quick Start

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t mops-financial-api .
docker run -p 8000:8000 mops-financial-api
```
