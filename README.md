# 🐟 AquaInsight — Norwegian Aquaculture Data Platform

**An end-to-end data engineering and analytics platform for Norwegian aquaculture health data.**

AquaInsight is a Python-based portfolio project demonstrating how publicly available aquaculture observations can be collected, processed, validated, stored, analyzed, and visualized using an integrated data platform.

The project analyzes **613,601 locality-week observations from 2015–2025**, sourced from BarentsWatch Fishhealth data.

---

## 1. Project Overview

AquaInsight implements an end-to-end data engineering pipeline:

**BarentsWatch API → Python ETL → Apache Parquet → PostgreSQL → FastAPI → Streamlit**

The platform provides:

- Data ingestion and cleaning workflows.
- Structured PostgreSQL storage and analytical SQL views.
- REST API endpoints for querying aquaculture statistics.
- Interactive visualizations of sea-lice trends and production-area performance.
- Data-quality monitoring and reporting-status analysis.
- Automated testing and Continuous Integration using GitHub Actions.

### Project Objectives

The primary objectives are to:

1. Build a reproducible data engineering pipeline using real aquaculture data.
2. Implement data cleaning, transformation, and quality validation.
3. Store structured data in PostgreSQL.
4. Develop analytical SQL queries and database views.
5. Expose analytical results through a REST API.
6. Build an interactive dashboard.
7. Implement automated testing and Continuous Integration.
8. Demonstrate practical data engineering and analytical skills.

---

## 2. Project Status

**Status: Active Development — Core Data Platform Implemented and Tested**

The following components are operational in the local development environment:

- Python ETL pipeline
- Parquet-based data processing
- PostgreSQL database
- SQL analytical views
- FastAPI backend
- Streamlit dashboard
- Data-quality analysis
- Automated tests
- GitHub Actions Continuous Integration

The project currently includes **40 automated tests**, successfully executed locally and through GitHub Actions.

Further development focuses on deployment reproducibility, documentation, and additional analytical capabilities.

---

### System Architecture

View the complete architecture diagram and technical details:

[AquaInsight System Architecture](docs/ARCHITECTURE.md)

## 3. Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python 3.12 |
| Data Processing | pandas, NumPy |
| Data Storage | PostgreSQL, Apache Parquet |
| Database Integration | SQLAlchemy, psycopg |
| Data Engineering | ETL pipelines, data cleaning, validation |
| Backend API | FastAPI, Pydantic, Uvicorn |
| Dashboard | Streamlit, Plotly |
| Testing | pytest, unittest.mock |
| Continuous Integration | GitHub Actions |
| Version Control | Git, GitHub |
| Development Environment | Ubuntu Linux, Conda |

### Planned Improvements

- Containerization using Docker
- Additional statistical and predictive analyses
- Automated data-refresh workflows
- Improved deployment and monitoring

---

## 4. Data Source

### BarentsWatch Fishhealth

**Source:** BarentsWatch — Norwegian Fishhealth Data

**Reporting period:** 2015–2025

**Dataset size:** 613,601 locality-week observations

The dataset contains information about Norwegian aquaculture localities, including:

- Reporting year and week
- Locality identifiers
- Geographic coordinates
- Adult female sea-lice measurements
- Mobile and attached sea-lice stages
- Sea temperature
- Production areas
- Sea-lice reporting status
- Applicable sea-lice thresholds
- Threshold exceedance indicators

Data source documentation:

[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

### Data Handling

Raw and processed datasets are excluded from Git version control.

This helps maintain a manageable repository size and keeps locally generated datasets separate from the application source code.

Data access and reuse remain subject to the applicable source terms.

---

## 5. Data Engineering Pipeline

AquaInsight processes Norwegian aquaculture observations through the following stages.

### Stage 1 — Data Ingestion

Retrieve historical aquaculture observations from the BarentsWatch Fishhealth API.

### Stage 2 — Data Cleaning

Process the downloaded data using Python and pandas.

Cleaning operations include:

- Column-name standardization
- Data-type conversion
- Missing-value handling
- Reporting-status validation
- Temperature outlier detection
- Sea-lice measurement validation

### Stage 3 — Data Validation

Validate the processed observations using automated checks.

Examples include:

- Required-column validation
- Reporting-conflict detection
- Sea-lice threshold calculations
- Annual observation counts
- Data-quality consistency checks

### Stage 4 — Parquet Storage

Store processed datasets using Apache Parquet.

Parquet provides an efficient columnar storage format for analytical workloads.

### Stage 5 — PostgreSQL

Load processed observations into PostgreSQL.

The database supports structured storage and SQL-based analysis.

### Stage 6 — Analytical SQL Views

The platform implements three analytical views:

1. Annual sea-lice summary
2. Production-area annual statistics
3. Annual data-quality statistics

### Stage 7 — REST API

FastAPI exposes analytical results to external applications.

### Stage 8 — Interactive Dashboard

Streamlit retrieves data from FastAPI and presents interactive analytical visualizations.

---

## 5A. Pipeline Reliability and Incremental Ingestion

### Historical ETL Orchestration

AquaInsight includes a Python orchestration layer for managing
historical data consolidation and cleaning.

The orchestration workflow:

1. Checks whether expected outputs already exist.
2. Validates existing outputs against reference datasets.
3. Skips valid processing stages.
4. Rebuilds missing or invalid outputs.
5. Uses atomic Parquet writes to protect existing valid files.
6. Stops execution if a processing stage fails.

The primary orchestration entry point is:

`orchestration/run_pipeline.py`

Atomic file writing is implemented in:

`orchestration/atomic_writer.py`

The current historical workflow requires locally available
BarentsWatch source files and reference datasets.

### Incremental PostgreSQL Ingestion

AquaInsight also includes a validated incremental ingestion prototype.

The ingestion process:

1. Validates the expected 28-column dataset structure.
2. Validates primary-key values and detects duplicate keys.
3. Checks PostgreSQL-compatible column types.
4. Converts missing values to database-compatible NULL values.
5. Classifies observations as INSERT, UPDATE, or SKIP.
6. Executes parameterized PostgreSQL upserts in batches.
7. Uses transactions to roll back failed ingestion operations.
8. Reports inserted, updated, unchanged, and affected records.

The composite primary key is:

`(year, week, locality_id)`

The implementation is organized into the following modules:

| Module | Responsibility |
|---|---|
| `src/incremental_fishhealth.py` | Input validation and record preparation |
| `src/incremental_type_validation.py` | Strict data-type validation |
| `src/incremental_upsert.py` | Parameterized PostgreSQL upsert construction |
| `src/incremental_metrics.py` | INSERT, UPDATE, and SKIP classification |
| `src/incremental_loader.py` | Batch execution and transaction management |

### Current Implementation Limitations

The incremental ingestion system has been tested using isolated
PostgreSQL temporary tables.

**Production incremental database writes are not enabled.**

INSERT and UPDATE classifications are determined before upsert
execution and are not concurrency-safe for simultaneous writers.

The current classification implementation also executes a database
query for each observation, which is inefficient for large datasets.

Future development should introduce set-based ingestion, concurrency
controls, and production-specific operational safeguards.

These limitations are intentionally documented to distinguish
validated prototype functionality from production-ready capabilities.

---

## 6. FastAPI Backend

AquaInsight provides six REST API endpoints.

| Endpoint | Purpose |
|---|---|
| `/api/v1/health` | Check API status |
| `/api/v1/database/health` | Check PostgreSQL connectivity |
| `/api/v1/annual-summary` | Retrieve annual aquaculture statistics |
| `/api/v1/production-areas/{year}` | Retrieve production-area statistics |
| `/api/v1/available-years` | Retrieve available reporting years |
| `/api/v1/data-quality` | Retrieve annual data-quality statistics |

FastAPI provides interactive API documentation through Swagger UI.

When the API is running locally, documentation is available at:

`http://127.0.0.1:8000/docs`

---

## 7. Streamlit Dashboard

The Streamlit dashboard provides an interactive interface for exploring Norwegian aquaculture health statistics.

### Implemented Features

**National Overview**

- Total observations
- Eligible compliance observations
- Sea-lice exceedances
- Overall exceedance percentage

**Historical Sea-Lice Analysis**

- Annual sea-lice statistics
- Historical exceedance trends

**Production-Area Analysis**

- Reporting-year selection
- Production-area statistics
- Comparative exceedance-rate visualization

**Data-Quality Analysis**

- Missing sea-lice measurements
- Annual missing-data trends
- Reporting-status classification
- Potential reporting-conflict detection
- Observation-count reconciliation

### Reporting-Status Analysis

The platform distinguishes between:

- Observations probably without fish where lice were not counted
- Observations not flagged as without fish where lice were not counted
- Observations where lice were counted

This distinction is important because missing measurements do not necessarily indicate reporting errors.

---

## 8. Installation and Testing

### Prerequisites

- Python 3.12
- Git
- Conda (recommended)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Kaziaa/aquaculture-data-platform.git
cd aquaculture-data-platform
```

### Step 2 — Create a Python Environment

```bash
conda create -n aquainsight python=3.12 pip -y
conda activate aquainsight
```

### Step 3 — Install Dependencies

```bash
python -m pip install -r requirements.txt
```

The dependency file contains pinned versions of the project's Python packages.

Installation has been verified in a clean Python 3.12 Conda environment.

### Step 4 — Run Automated Tests

```bash
python -m pytest tests/ -v
```

The test suite includes 40 automated tests covering:

- FastAPI endpoints
- API response validation
- Database connection lifecycle using mocks
- Data cleaning
- Reporting-status validation
- Data-quality checks
- ETL integration using synthetic data

The complete test suite requires an initialized PostgreSQL database for integration testing. The historical dataset is not required because integration tests use synthetic fixtures.

### Expected Test Result

```text
40 passed
```

A non-failing dependency deprecation warning may also appear.

---


### PostgreSQL Setup Guide

For database configuration, schema initialization, historical loading, and integration testing, see:

[PostgreSQL Database Setup](docs/DATABASE_SETUP.md)

---

## 9. Running the Application Locally

**Important:** The complete application requires a configured PostgreSQL database containing the processed aquaculture observations.

The installation steps above are sufficient to install dependencies and run automated tests, but they do not automatically populate PostgreSQL.

### Start the FastAPI Backend

From the project root, run:

```bash
uvicorn api.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### Start the Streamlit Dashboard

Open another terminal, activate the Python environment, and navigate to the project directory.

Run:

```bash
streamlit run dashboard/app.py
```

The dashboard will normally be available at:

`http://localhost:8501`

### Application Dependencies

The dashboard communicates with the FastAPI backend.

The backend retrieves analytical results from PostgreSQL.

Both the database and API must therefore be correctly configured for the full dashboard to function.

---

## 10. Continuous Integration

AquaInsight uses **GitHub Actions** for automated testing.

The workflow runs when:

- Code is pushed to the `main` branch.
- A pull request targets the `main` branch.

### CI Workflow

The workflow performs the following operations:

1. Checks out the repository.
2. Configures Python 3.12.
3. Installs project dependencies.
4. Executes the automated pytest suite.

Workflow configuration:

`.github/workflows/tests.yml`

### CI Status

**GitHub Actions: Successfully verified**

The workflow has successfully completed after correcting tests that previously depended on local credentials and historical datasets.

This ensures the automated test suite can execute in a GitHub-hosted environment.

---

## 11. Data Quality and Validation

Data quality is a central component of AquaInsight.

The platform evaluates:

- Missing measurements
- Reporting completeness indicators
- Reporting-status categories
- Potential reporting conflicts
- Sea-temperature outliers
- Sea-lice threshold exceedances
- Aggregate observation-count consistency

### Historical Data-Quality Results

Across 2015–2025:

| Metric | Observations |
|---|---:|
| Total observations | 613,601 |
| Adult female lice measurements missing | 296,166 |
| Probably without fish — lice not counted | 285,609 |
| Not flagged as without fish — lice not counted | 10,557 |
| Lice counted | 317,435 |
| Potential reporting conflicts | 34 |

**Important:** Missing adult female lice measurements must not automatically be interpreted as reporting failures.

The reporting-status fields provide essential context for interpreting missing values.

The 34 potential reporting conflicts are already included within the lice-counted category and are not additional observations.

---

## 12. Automated Testing Strategy

AquaInsight uses several complementary testing approaches.

### Unit Testing

Tests individual data-cleaning and validation functions.

### API Testing

Tests FastAPI endpoints, response models, and error handling.

Database interactions are mocked where appropriate.

### Integration Testing

Uses a small synthetic dataset to execute the actual ETL pipeline.

The integration test verifies:

- Data transformations
- Missing-value handling
- Reporting-conflict detection
- Temperature validation
- Sea-lice exceedance calculations
- Annual aggregation
- Parquet output

This approach allows the test suite to run without downloading the complete historical dataset.

### Historical Data Validation

The complete historical dataset is used for local analytical verification.

This is separate from the synthetic-data integration tests executed by GitHub Actions.

---

## 13. Project Reproducibility

The following components have been verified:

- Python dependency installation in a clean environment
- Automated unit tests
- API tests using mocks
- Synthetic-data ETL integration tests
- GitHub Actions Continuous Integration

### Current Limitations

The complete data platform is not yet packaged for fully automated deployment from scratch.

Additional configuration is required for:

- PostgreSQL installation and configuration
- Database schema initialization
- Historical data ingestion
- Application environment variables
- Full application startup

Detailed deployment instructions are under development.

---

## 14. Future Development

Planned improvements include:

- Docker-based deployment
- Automated data-refresh workflows
- Additional statistical analyses
- Enhanced dashboard functionality
- Improved application monitoring
- More comprehensive deployment documentation

These features are planned and are not presented as completed functionality.

---

## 15. Project Purpose

AquaInsight was developed as a practical portfolio project to demonstrate capabilities in:

- Python programming
- Data engineering
- ETL pipeline development
- SQL and relational databases
- REST API development
- Data-quality engineering
- Data visualization
- Software testing
- Continuous Integration
- Reproducible analytical workflows

The project combines real-world aquaculture data with modern data engineering practices.

---

## 16. License

A software license has not yet been selected.

Third-party datasets remain subject to their respective licensing and usage terms.
