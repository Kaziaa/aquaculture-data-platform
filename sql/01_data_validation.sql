CREATE SCHEMA IF NOT EXISTS aquainsight
AUTHORIZATION aquainsight_user;

CREATE TABLE IF NOT EXISTS aquainsight.fishhealth_weekly (

    -- Observation identifiers
    year BIGINT NOT NULL,
    week BIGINT NOT NULL,
    locality_id BIGINT NOT NULL,
    locality_name TEXT,

    -- Sea-lice measurements
    adult_female_lice DOUBLE PRECISION,
    mobile_lice DOUBLE PRECISION,
    attached_lice DOUBLE PRECISION,

    -- Reporting information
    probably_without_fish BOOLEAN,
    lice_counted BOOLEAN,

    -- Administrative information
    municipality_id BIGINT,
    municipality TEXT,
    county_id BIGINT,
    county TEXT,

    -- Geographic coordinates
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- Compliance information
    weekly_lice_limit DOUBLE PRECISION,
    over_lice_limit BOOLEAN,

    -- Environmental information
    sea_temperature DOUBLE PRECISION,

    -- Production area
    production_area_id BIGINT,
    production_area TEXT,

    -- Original source value
    weekly_lice_limit_original TEXT,

    -- Data quality indicators
    reporting_conflict BOOLEAN,
    temperature_outlier BOOLEAN,
    sea_temperature_clean DOUBLE PRECISION,

    -- Extreme lice indicators
    adult_female_lice_extreme BOOLEAN,
    mobile_lice_extreme BOOLEAN,
    attached_lice_extreme BOOLEAN,

    -- Calculated compliance
    calculated_lice_exceedance BOOLEAN,

    -- Composite primary key
    CONSTRAINT pk_fishhealth_weekly
        PRIMARY KEY (year, week, locality_id)
);



------------Verify the PostgreSQL Table Before Importing Data---------------
SELECT
    COUNT(*) AS total_records
FROM aquainsight.fishhealth_weekly;


------------------###---------------
SELECT COUNT(*) AS total_records
FROM aquainsight.fishhealth_weekly;


----------------### Data oimported isign python -----------------

------------## verify
SELECT
    COUNT(*) AS total_records,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT locality_id) AS unique_localities
FROM aquainsight.fishhealth_weekly;
