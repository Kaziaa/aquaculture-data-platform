# AquaInsight — PostgreSQL Database Setup

## 1. Overview

AquaInsight uses PostgreSQL 16 to store and analyze Norwegian aquaculture health observations. The historical 2015–2025 dataset contains 613,601 locality-week observations, 28 columns, and a composite primary key of `(year, week, locality_id)`.

The schema is defined in `sql/00_init_database.sql`.

## 2. Prerequisites

- PostgreSQL 16
- Python 3.12
- Project dependencies from `requirements.txt`
- A dedicated PostgreSQL role and database

## 3. Configure database credentials

From the project root, copy the template:

```bash
cp .env.example .env
```

Edit `.env` to set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for **your own** database. Never commit `.env` or real passwords.

## 4. Create a fresh database

In a PostgreSQL administrator session, create a role and a new, empty database **only if they do not already exist**:

```sql
CREATE ROLE aquainsight_user WITH LOGIN PASSWORD 'choose_a_secure_password';
CREATE DATABASE aquainsight OWNER aquainsight_user;
```

The schema script expects the role `aquainsight_user`. Match the database credentials in `.env` to the role and database you created. These are examples for a new installation; do not run role or database creation commands against a setup you already use.

## 5. Initialize the 28-column schema

From the repository root, run the following **only for the newly created development database**:

```bash
psql -h localhost -U aquainsight_user -d aquainsight -v ON_ERROR_STOP=1 -f sql/00_init_database.sql
```

This creates `aquainsight.fishhealth_weekly` with the primary key `(year, week, locality_id)`.

## 6. Historical initial import

The historical loader is `scripts/load_postgres.py`. Its configured source is:

`data/processed/barentswatch_lice_pipeline_2015_2025.parquet`

It expects **exactly 613,601 rows and 28 columns**. Historical Parquet data is not committed to Git; it must first be obtained and processed using the project's ingestion and transformation workflows.

The loader's current settings include:

```python
TEST_MODE = True
TEST_ROWS = 100
BATCH_SIZE = 1000
```

Test mode inserts 100 observations into an **empty** target table, verifies the count, then rolls the transaction back. Full import mode (`TEST_MODE = False`) imports the full dataset and commits after verification. In both modes, the loader rejects a nonempty destination table.

**Do not run the loader against your existing populated database.** For a new deployment, inspect the settings and `DB_NAME` before starting an import. The loader is specific to the 2015–2025 historical snapshot; it is not a general-purpose refresh mechanism.

## 7. Incremental-ingestion prototype

The modules `src/incremental_fishhealth.py`, `src/incremental_type_validation.py`, `src/incremental_upsert.py`, `src/incremental_metrics.py`, and `src/incremental_loader.py` demonstrate strict validation, SQL upserts, INSERT/UPDATE/SKIP classification, batching, and transactional rollback.

**Production incremental writes are not enabled.** The current loader writes to PostgreSQL temporary tables for testing. Its per-observation classification is inefficient for large volumes and is not concurrency-safe for multiple simultaneous writers.

## 8. Automated testing

AquaInsight currently has **40 Python tests**. Some are PostgreSQL integration tests and need an initialized schema. Test data is provided in `tests/fixtures/fishhealth_sample.parquet`; the historical dataset is not required to run the tests.

Use an isolated database (for example, `aquainsight_test`) and configure the environment to connect to it before running:

```bash
python -m pytest tests/ -v
```

The SQL test runner `sql/05_run_database_tests.sql` is destructive within its test database (it uses `TRUNCATE`) and explicitly requires the database name `aquainsight_test`. **Never execute it against a database containing valuable records.**

## 9. Continuous integration

`.github/workflows/tests.yml` defines two independent GitHub Actions jobs:

1. **Python Tests:** starts PostgreSQL 16, initializes the schema, then runs pytest.
2. **PostgreSQL SQL Tests:** executes analytical SQL validation against a separate disposable test database.

## 10. Current limitations

- Historical data files are excluded from Git.
- Initial import is tied to a particular validated dataset snapshot.
- End-to-end deployment from a new machine is not yet fully automated.
- Production incremental ingestion, concurrency controls, and set-based performance optimization remain future work.
