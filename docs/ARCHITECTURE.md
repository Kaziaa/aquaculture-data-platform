# AquaInsight — System Architecture

## Overview

AquaInsight is a Python-based Norwegian aquaculture data platform.

It combines data ingestion, ETL processing, PostgreSQL analytics,
FastAPI services, and Streamlit visualization.

## Architecture Diagram

```mermaid
flowchart TD
    A["BarentsWatch Fishhealth API"] --> B["Python Data Ingestion"]
    B --> C["Historical CSV Files"]
    C --> D["ETL Orchestration"]
    D --> E["Data Consolidation"]
    E --> F["Data Cleaning and Validation"]
    F --> G["Atomic Parquet Storage"]
    G --> H["Historical PostgreSQL Loader"]
    H --> I[("PostgreSQL Database")]
    I --> J["Analytical SQL Views"]
    J --> K["FastAPI REST API"]
    K --> L["Streamlit Dashboard"]

    M["Incoming Test Observations"] --> N["Incremental Validation"]
    N --> O["Batch UPSERT and Metrics"]
    O --> P[("Temporary PostgreSQL Tables")]

    Q["pytest and GitHub Actions"] -.-> D
    Q -.-> K
    Q -.-> O
## Technology Stack

| Component | Technology |
|---|---|
| Data Processing | Python, pandas |
| Database | PostgreSQL 16 |
| Backend | FastAPI |
| Dashboard | Streamlit |
| Testing | pytest, GitHub Actions |

## Pipeline Reliability

- Atomic Parquet writes
- Data validation
- Pipeline orchestration
- Transaction rollback

## Incremental Ingestion

The incremental ingestion prototype supports PostgreSQL upserts,
INSERT/UPDATE/SKIP classification, and batch processing.

Production incremental writes are not yet enabled.

## Limitations

- Historical datasets are excluded from Git.
- Production incremental ingestion requires further development.
- Automated deployment is not yet implemented.
