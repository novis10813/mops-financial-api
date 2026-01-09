-- Migration: Create monthly_revenue table
-- Date: 2024-01-09
-- Description: Add table for caching MOPS monthly revenue data

CREATE TABLE IF NOT EXISTS monthly_revenue (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    company_name VARCHAR(100),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    market VARCHAR(10) DEFAULT 'sii',
    
    -- 營收數據 (單位: 千元)
    revenue NUMERIC(20, 0),
    revenue_last_month NUMERIC(20, 0),
    revenue_last_year NUMERIC(20, 0),
    
    -- 增減率 (%)
    mom_change NUMERIC(10, 2),
    yoy_change NUMERIC(10, 2),
    
    -- 累計營收
    accumulated_revenue NUMERIC(20, 0),
    accumulated_last_year NUMERIC(20, 0),
    accumulated_yoy_change NUMERIC(10, 2),
    
    -- 備註
    comment TEXT,
    
    -- Metadata
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint
ALTER TABLE monthly_revenue 
ADD CONSTRAINT uq_revenue_identity 
UNIQUE (stock_id, year, month, market);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_revenue_stock_id ON monthly_revenue(stock_id);
CREATE INDEX IF NOT EXISTS ix_revenue_lookup ON monthly_revenue(stock_id, year, month);
CREATE INDEX IF NOT EXISTS ix_revenue_period ON monthly_revenue(year, month, market);

-- Comments
COMMENT ON TABLE monthly_revenue IS '月營收資料';
COMMENT ON COLUMN monthly_revenue.stock_id IS '股票代號';
COMMENT ON COLUMN monthly_revenue.year IS '民國年';
COMMENT ON COLUMN monthly_revenue.month IS '月份 1-12';
COMMENT ON COLUMN monthly_revenue.market IS '市場: sii/otc/rotc/pub';
COMMENT ON COLUMN monthly_revenue.revenue IS '當月營收 (千元)';
COMMENT ON COLUMN monthly_revenue.yoy_change IS '去年同月增減率 (%)';
COMMENT ON COLUMN monthly_revenue.accumulated_revenue IS '當月累計營收';
