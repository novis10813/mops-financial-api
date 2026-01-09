# Additional MOPS Crawlers - Changelog

## [Unreleased]

### Added
- Branch `feat/additional-crawlers` created from `main`

### Documentation (Phase 1-3)
- `REQUIREMENTS.md` - Feature requirements documenting 6 new data sources:
  - 月營收 (Monthly Revenue) - P0 Priority
  - 背書保證與資金貸與 (Endorsements & Lending) - P1 Priority
  - 董監事質押 (Share Pledging) - P1 Priority
  - 股利分派 (Dividend Policy) - P2 Priority
  - 衍生性商品 (Derivatives) - P3 Priority
  - 資本形成 (Capital Structure) - P3 Priority

- `DESIGN.md` - Comprehensive architecture design:
  - 4-Router architecture (revenue, risk, insiders, corporate)
  - 3 Critical Design Points:
    1. Year Transformation (西元年 in API, 民國年 internal)
    2. Read vs Force Update separation
    3. Bulk vs Specific query support
  - Database schema for 7 new tables
  - Pydantic models for all data types
  - MOPS URL patterns identified

- `IMPLEMENTATION_STEPS.md` - 17-step implementation plan:
  - Step 0: MOPS HTML Client (基礎設施)
  - Steps 1-4: P0 月營收
  - Steps 5-8: P1 董監事質押
  - Steps 9-12: P1 背書保證
  - Steps 13-16: P2/P3 features
  - Step 17: 整合測試與文檔

### Design Decisions
- ✅ Router structure: 4 Routers agreed with Gemini
- ✅ Time format: API uses AD year, internal converts to ROC
- ✅ Query mode: Support both market-wide and single stock

### Pending Implementation
- [ ] Step 0: MOPS HTML Client
- [ ] Step 1-4: 月營收 (P0)
- [ ] Step 5-8: 董監事質押 (P1)
- [ ] Step 9-12: 背書保證 (P1)
- [ ] Step 13-16: P2/P3 features
- [ ] Step 17: Integration tests
