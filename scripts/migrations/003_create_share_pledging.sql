-- Migration: Create share_pledging table
-- Date: 2024-01-09
-- Description: Add table for caching MOPS share pledging data

CREATE TABLE IF NOT EXISTS share_pledging (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    company_name VARCHAR(100),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    
    -- 職位資訊
    title VARCHAR(50),
    relationship VARCHAR(20) DEFAULT '本人',
    name VARCHAR(100),
    
    -- 持股資訊
    shares_at_election NUMERIC(20, 0),
    current_shares NUMERIC(20, 0),
    pledged_shares NUMERIC(20, 0),
    pledge_ratio NUMERIC(10, 2),
    
    -- Metadata
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint
ALTER TABLE share_pledging 
ADD CONSTRAINT uq_pledging_identity 
UNIQUE (stock_id, year, month, title, name);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_pledging_stock_id ON share_pledging(stock_id);
CREATE INDEX IF NOT EXISTS ix_pledging_lookup ON share_pledging(stock_id, year, month);
CREATE INDEX IF NOT EXISTS ix_pledging_high_ratio ON share_pledging(pledge_ratio);

-- Comments
COMMENT ON TABLE share_pledging IS '董監事質押資料';
COMMENT ON COLUMN share_pledging.stock_id IS '股票代號';
COMMENT ON COLUMN share_pledging.title IS '職稱 (董事長/獨立董事/副總經理等)';
COMMENT ON COLUMN share_pledging.pledge_ratio IS '設質比例 (%)';
