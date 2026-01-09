# Code Review Fixes - Implementation Steps

## Step 1: Preparation
- [ ] Review `app/utils/numerics.py` to ensure `parse_financial_value` covers all existing logic in services (e.g. strict checks, dash handling).

## Step 2: Extract Schemas
- [ ] Create `app/schemas/revenue.py` and move `MonthlyRevenue` from `app/services/revenue.py`.
- [ ] Create `app/schemas/dividend.py` and move `DividendResponse` from `app/services/dividend.py`.
- [ ] Create `app/schemas/disclosure.py` and move `DisclosureResponse` from `app/services/disclosure.py`.

## Step 3: Update Routers
- [ ] Update `app/routers/revenue.py` imports.
- [ ] Update `app/routers/dividend.py` imports.
- [ ] Update `app/routers/disclosure.py` imports.

## Step 4: Refactor Services - Part 1 (Imports & Parsing)
- [ ] **RevenueService**:
    - [ ] Import `MonthlyRevenue` from `app/schemas/revenue.py`.
    - [ ] Import `parse_financial_value` from `app/utils/numerics.py`.
    - [ ] Remove `_parse_number`, `_parse_float`.
    - [ ] Replace usage in `_parse_revenue_tables`.
- [ ] **DividendService**:
    - [ ] Import `DividendResponse`.
    - [ ] Import `parse_financial_value`.
    - [ ] Remove internal parsing helpers.
    - [ ] Replace usage.
- [ ] **DisclosureService**:
    - [ ] Import `DisclosureResponse`.
    - [ ] Import `parse_financial_value`.
    - [ ] Remove internal parsing helpers.
    - [ ] Replace usage.

## Step 5: Refactor Services - Part 2 (Error Handling)
- [ ] **RevenueService**: Replace broad `except Exception` with structured logging.
- [ ] **DividendService**: Replace broad `except Exception` with structured logging.
- [ ] **DisclosureService**: Replace broad `except Exception` with structured logging.

## Step 6: Verification
- [ ] Run `pytest` to ensure all tests pass.
- [ ] Verify API endpoints manually (optional but recommended).
