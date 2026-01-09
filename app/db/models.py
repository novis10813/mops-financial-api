"""
Database Models for Financial Reports Storage

Tables:
- companies: Company master data
- financial_reports: Report metadata + full JSON backup
- financial_facts: Flattened financial items for fast queries
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    ForeignKey, Index, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass


class Company(Base):
    """
    公司基本資料
    
    用於快速查詢公司名稱和產業分類
    """
    __tablename__ = "companies"
    
    stock_id = Column(String(10), primary_key=True, comment="股票代號")
    name = Column(String(100), nullable=False, comment="公司名稱")
    name_en = Column(String(100), comment="英文名稱")
    industry = Column(String(50), comment="產業分類")
    market = Column(String(20), comment="市場: TWSE/TPEx")
    updated_at = Column(
        DateTime, 
        server_default="now()", 
        onupdate=datetime.utcnow,
        comment="更新時間"
    )
    
    # Relationships
    reports = relationship("FinancialReport", back_populates="company")
    
    def __repr__(self):
        return f"<Company {self.stock_id} {self.name}>"


class FinancialReport(Base):
    """
    財務報表基本資訊
    
    每一筆代表一份完整的財務報表（如 2330 113年Q3 資產負債表）
    """
    __tablename__ = "financial_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(String(10), ForeignKey("companies.stock_id"), nullable=False, comment="股票代號")
    year = Column(Integer, nullable=False, comment="民國年")
    quarter = Column(Integer, nullable=False, comment="季度 1-4")
    report_type = Column(String(30), nullable=False, comment="報表類型: balance_sheet, income_statement, cash_flow")
    
    # 完整報表 JSON (包含完整階層結構)
    full_data = Column(JSONB, nullable=True, comment="完整報表 JSON")
    
    # Metadata
    fetched_at = Column(DateTime, server_default="now()", comment="抓取時間")
    source = Column(String(50), default="mops", comment="資料來源")
    is_standalone = Column(Boolean, default=False, comment="是否為單季資料（Q4）")
    
    # Relationships
    company = relationship("Company", back_populates="reports")
    facts = relationship("FinancialFact", back_populates="report", cascade="all, delete-orphan")
    
    __table_args__ = (
        # 確保同一份報表不會重複
        UniqueConstraint("stock_id", "year", "quarter", "report_type", name="uq_report_identity"),
        # 查詢索引
        Index("ix_report_lookup", "stock_id", "year", "quarter", "report_type"),
        Index("ix_report_stock", "stock_id"),
        {"comment": "財務報表"}
    )
    
    def __repr__(self):
        return f"<FinancialReport {self.stock_id} {self.year}Q{self.quarter} {self.report_type}>"


class FinancialFact(Base):
    """
    扁平化財務項目
    
    將報表中的每個科目（如資產、負債、營收）展開為一筆記錄
    便於快速查詢特定科目數值
    
    Example:
        SELECT value FROM financial_facts 
        WHERE concept = 'Revenue' AND stock_id = '2330' AND year = 113
    """
    __tablename__ = "financial_facts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(
        Integer, 
        ForeignKey("financial_reports.id", ondelete="CASCADE"), 
        nullable=False,
        comment="所屬報表 ID"
    )
    
    # 科目資訊
    concept = Column(String(255), nullable=False, comment="XBRL concept (e.g., Assets, Revenue)")
    label_zh = Column(String(200), comment="中文名稱")
    label_en = Column(String(200), comment="英文名稱")
    
    # 數值 (使用 Numeric 確保精確度)
    value = Column(Numeric(20, 4), nullable=True, comment="數值")
    
    # 階層資訊 (選用)
    level = Column(Integer, default=0, comment="階層深度")
    weight = Column(Numeric(3, 1), default=1.0, comment="權重 (+1/-1)")
    
    # Relationships
    report = relationship("FinancialReport", back_populates="facts")
    
    __table_args__ = (
        # 查詢索引
        Index("ix_fact_concept", "concept"),
        Index("ix_fact_report", "report_id"),
        # 複合索引：快速查詢特定報表的特定科目
        Index("ix_fact_report_concept", "report_id", "concept"),
        {"comment": "財務科目明細"}
    )
    
    def __repr__(self):
        return f"<FinancialFact {self.concept}={self.value}>"


class MonthlyRevenue(Base):
    """
    月營收資料
    
    用於快取 MOPS 月營收資料，避免每次都爬取
    
    Source:
    https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html
    """
    __tablename__ = "monthly_revenue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(String(10), nullable=False, index=True, comment="股票代號")
    company_name = Column(String(100), comment="公司名稱")
    year = Column(Integer, nullable=False, comment="民國年")
    month = Column(Integer, nullable=False, comment="月份 1-12")
    market = Column(String(10), default="sii", comment="市場: sii/otc/rotc/pub")
    
    # 營收數據 (單位: 千元)
    revenue = Column(Numeric(20, 0), comment="當月營收")
    revenue_last_month = Column(Numeric(20, 0), comment="上月營收")
    revenue_last_year = Column(Numeric(20, 0), comment="去年當月營收")
    
    # 增減率 (%)
    mom_change = Column(Numeric(10, 2), comment="上月比較增減率 (%)")
    yoy_change = Column(Numeric(10, 2), comment="去年同月增減率 (%)")
    
    # 累計營收
    accumulated_revenue = Column(Numeric(20, 0), comment="當月累計營收")
    accumulated_last_year = Column(Numeric(20, 0), comment="去年累計營收")
    accumulated_yoy_change = Column(Numeric(10, 2), comment="前期比較增減率 (%)")
    
    # 備註
    comment = Column(Text, comment="備註說明")
    
    # Metadata
    fetched_at = Column(DateTime, server_default="now()", comment="抓取時間")
    
    __table_args__ = (
        # 確保同一月份同一公司不會重複
        UniqueConstraint("stock_id", "year", "month", "market", name="uq_revenue_identity"),
        # 查詢索引
        Index("ix_revenue_lookup", "stock_id", "year", "month"),
        Index("ix_revenue_period", "year", "month", "market"),
        {"comment": "月營收資料"}
    )
    
    def __repr__(self):
        return f"<MonthlyRevenue {self.stock_id} {self.year}/{self.month}>"
