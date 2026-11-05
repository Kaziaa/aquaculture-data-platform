# PROJECT PLAN — 4 November–10 December 2026

**Target:** 37 sessions × 2 hours = **74 hours**. One session per calendar day. If a session slips, record the change in `PROGRESS.md`; do not mark work complete without evidence.

## Operating rules

- Build only with freely available/local tools. Do not require billing, paid cloud or credit card.
- Use the existing, real Norwegian fish-health observations; record the data owner, license/terms, access date, and source URL before republishing any subset.
- Do **not** push large raw datasets, credentials, model artifacts or private information to GitHub.
- A checkbox is complete only when its `Done when` acceptance criterion is demonstrated.
- Each session: 10 minutes plan, 90 minutes build, 15 minutes test/document, 5 minutes commit and log.
- Aim to commit each session. Push to GitHub when connected; never push broken secrets or raw data.
- No predictive claim unless the label, temporal split and leakage audit are defensible. Otherwise publish a rigorous descriptive/statistical analysis.

## Milestone tracker

| Phase | Date range | Hours | Acceptance gate |
|---|---|---:|---|
| Foundation | 4–8 Nov | 10 | Source provenance, inspection and validated data import functions |
| SQL and PostgreSQL | 9–15 Nov | 14 | Database schema, idempotent import, validated analytical SQL |
| Automated ETL | 16–22 Nov | 14 | Reproducible, tested end-to-end processing |
| Interactive dashboard | 23–29 Nov | 14 | Streamlit dashboard driven by PostgreSQL and tested filters |
| Data science | 30 Nov–6 Dec | 14 | EDA + credible baseline/model results or justified non-ML analysis |
| Release and applications | 7–10 Dec | 8 | Docker/local deployment, CI, portfolio README, tagged release |

## Daily checklist

Mark a task complete by changing `- [ ]` to `- [x]`. GitHub will render these as task-list checkboxes.

### Foundation

- [ ] **Day 01 — 2026-11-04** · Initialize repository and environment (2 h)  
  **Done when:** git status; Python environment activates. **Evidence:** `Git repository + requirements`.
- [ ] **Day 02 — 2026-11-05** · Locate original public data and document provenance (2 h)  
  **Done when:** Dataset available locally; source and license recorded. **Evidence:** `docs/DATA_SOURCES.md`.
- [ ] **Day 03 — 2026-11-06** · Inspect schema, missingness and duplicates (2 h)  
  **Done when:** Printed column types, null counts and duplicate counts. **Evidence:** `src/aquaculture/inspect_data.py`.
- [ ] **Day 04 — 2026-11-07** · Write data contract and validation rules (2 h)  
  **Done when:** Field definitions and 3 real quality checks. **Evidence:** `docs/DATA_DICTIONARY.md`.
- [ ] **Day 05 — 2026-11-08** · Implement first reusable clean/validate function (2 h)  
  **Done when:** Functions execute on a small real data sample; tests pass. **Evidence:** `src/aquaculture/clean.py`.

### SQL and PostgreSQL

- [ ] **Day 06 — 2026-11-09** · Install and run local PostgreSQL (2 h)  
  **Done when:** Database connection succeeds. **Evidence:** `docs/SETUP.md`.
- [ ] **Day 07 — 2026-11-10** · Design schema, primary and foreign keys (2 h)  
  **Done when:** SQL creates tables from scratch. **Evidence:** `sql/001_schema.sql`.
- [ ] **Day 08 — 2026-11-11** · Build idempotent initial import (2 h)  
  **Done when:** Repeated run does not duplicate rows. **Evidence:** `src/aquaculture/load.py`.
- [ ] **Day 09 — 2026-11-12** · Write 5 foundational SQL queries (2 h)  
  **Done when:** Queries return verified totals. **Evidence:** `sql/analytics.sql`.
- [ ] **Day 10 — 2026-11-13** · Use SQL joins, CTEs and window functions (2 h)  
  **Done when:** At least one query per technique works. **Evidence:** `sql/advanced_queries.sql`.
- [ ] **Day 11 — 2026-11-14** · Create analytical views for dashboard (2 h)  
  **Done when:** Views return expected metrics. **Evidence:** `sql/002_views.sql`.
- [ ] **Day 12 — 2026-11-15** · Reconcile database outputs against source data (2 h)  
  **Done when:** Counts and sample values verified. **Evidence:** `tests/test_reconciliation.py`.

### Automated ETL

- [ ] **Day 13 — 2026-11-16** · Separate extract, transform and load modules (2 h)  
  **Done when:** Modules callable independently. **Evidence:** `src/aquaculture/etl.py`.
- [ ] **Day 14 — 2026-11-17** · Add schema and range validation (2 h)  
  **Done when:** Invalid rows flagged; reasons recorded. **Evidence:** `tests/test_validation.py`.
- [ ] **Day 15 — 2026-11-18** · Handle duplicates and incremental loads (2 h)  
  **Done when:** Two runs yield same row count. **Evidence:** `tests/test_idempotency.py`.
- [ ] **Day 16 — 2026-11-19** · Add structured logs and error handling (2 h)  
  **Done when:** Failures produce actionable logs. **Evidence:** `src/aquaculture/logging_utils.py`.
- [ ] **Day 17 — 2026-11-20** · Implement simple orchestration (2 h)  
  **Done when:** One command runs entire ETL; scheduler optional. **Evidence:** `pipelines/run_pipeline.py`.
- [ ] **Day 18 — 2026-11-21** · Write pipeline integration tests (2 h)  
  **Done when:** Real small sample passes end-to-end. **Evidence:** `tests/test_pipeline.py`.
- [ ] **Day 19 — 2026-11-22** · Document pipeline architecture and decisions (2 h)  
  **Done when:** Diagram + commands to reproduce. **Evidence:** `docs/ARCHITECTURE.md`.

### Interactive dashboard

- [ ] **Day 20 — 2026-11-23** · Build Streamlit skeleton and DB connection (2 h)  
  **Done when:** App starts and queries PostgreSQL. **Evidence:** `dashboards/app.py`.
- [ ] **Day 21 — 2026-11-24** · Add KPI overview with transparent definitions (2 h)  
  **Done when:** KPIs reconcile to SQL views. **Evidence:** `dashboards/app.py`.
- [ ] **Day 22 — 2026-11-25** · Add time-series lice trend plot (2 h)  
  **Done when:** Date range filters work. **Evidence:** `dashboards/app.py`.
- [ ] **Day 23 — 2026-11-26** · Add locality and region filters (2 h)  
  **Done when:** Filtered counts match SQL. **Evidence:** `dashboards/app.py`.
- [ ] **Day 24 — 2026-11-27** · Add historical exceedance analysis (2 h)  
  **Done when:** Threshold assumptions and limits visible. **Evidence:** `dashboards/app.py`.
- [ ] **Day 25 — 2026-11-28** · Add data quality and missingness page (2 h)  
  **Done when:** Missing data is not silently hidden. **Evidence:** `dashboards/app.py`.
- [ ] **Day 26 — 2026-11-29** · Polish usability and capture screenshots (2 h)  
  **Done when:** Screenshots + consistent labeling. **Evidence:** `docs/screenshots/`.

### Data science

- [ ] **Day 27 — 2026-11-30** · Define question, outcome and leakage constraints (2 h)  
  **Done when:** Written feasibility and target definition. **Evidence:** `docs/MODELING_PLAN.md`.
- [ ] **Day 28 — 2026-12-01** · Perform EDA and descriptive statistics (2 h)  
  **Done when:** Plots + interpretation tied to question. **Evidence:** `reports/EDA.md`.
- [ ] **Day 29 — 2026-12-02** · Build temporal train/test split (2 h)  
  **Done when:** Train dates strictly before holdout. **Evidence:** `models/train.py`.
- [ ] **Day 30 — 2026-12-03** · Establish a simple baseline (2 h)  
  **Done when:** Baseline predictions + metrics recorded. **Evidence:** `reports/MODEL_RESULTS.md`.
- [ ] **Day 31 — 2026-12-04** · Train interpretable candidate model (2 h)  
  **Done when:** Model compared fairly with baseline. **Evidence:** `models/train.py`.
- [ ] **Day 32 — 2026-12-05** · Evaluate imbalance, calibration and error cases (2 h)  
  **Done when:** PR-AUC/recall or appropriate metrics; honest limitations. **Evidence:** `reports/MODEL_RESULTS.md`.
- [ ] **Day 33 — 2026-12-06** · Surface findings or safe predictions in dashboard (2 h)  
  **Done when:** Results labeled exploratory; no misleading claims. **Evidence:** `dashboards/app.py`.

### Release and applications

- [ ] **Day 34 — 2026-12-07** · Package local deployment with Docker Compose (2 h)  
  **Done when:** Fresh local run from documented commands. **Evidence:** `compose.yaml`.
- [ ] **Day 35 — 2026-12-08** · Add GitHub Actions CI for tests (2 h)  
  **Done when:** Push triggers passing checks. **Evidence:** `.github/workflows/tests.yml`.
- [ ] **Day 36 — 2026-12-09** · Polish README and architecture diagrams (2 h)  
  **Done when:** Install, screenshots, provenance, limitations clear. **Evidence:** `README.md`.
- [ ] **Day 37 — 2026-12-10** · Tag release and write CV/interview evidence (2 h)  
  **Done when:** v1.0 tag + 3 truthful resume bullets. **Evidence:** `docs/PORTFOLIO_SUMMARY.md`.

## Honest scope control

Priority order: **functional data import → database → dashboard → analytical insights → polished release**. If running behind, reduce advanced ML and orchestration scope rather than leaving a broken dashboard or undocumented repository.

## Check progress

Run `python scripts/progress.py` from repository root to count completed `[x]` entries in the daily checklist.
