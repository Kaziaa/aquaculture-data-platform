-- ============================================================
-- AquaInsight — Automated Analytical View Validation
--
-- Execute ONLY against aquainsight_test.
--
-- Expected dataset:
-- Four synthetic observations from sql/03_test_data.sql
--
-- A failed assertion raises a PostgreSQL exception.
-- ============================================================

DO $$
DECLARE
    actual_total BIGINT;
    actual_eligible BIGINT;
    actual_exceedances BIGINT;
    actual_percentage NUMERIC;
BEGIN

    -- --------------------------------------------------------
    -- Check 1: Annual observation count
    -- --------------------------------------------------------

    SELECT total_observations
    INTO STRICT actual_total
    FROM aquainsight.v_annual_lice_summary
    WHERE year = 2025;

    IF actual_total <> 4 THEN
        RAISE EXCEPTION
            'Annual observation count incorrect: %',
            actual_total;
    END IF;

    -- --------------------------------------------------------
    -- Check 2: Eligible observations
    -- --------------------------------------------------------

    SELECT eligible_compliance_observations
    INTO STRICT actual_eligible
    FROM aquainsight.v_annual_lice_summary
    WHERE year = 2025;

    IF actual_eligible <> 3 THEN
        RAISE EXCEPTION
            'Eligible observation count incorrect: %',
            actual_eligible;
    END IF;

    -- --------------------------------------------------------
    -- Check 3: Exceedance count and percentage
    -- --------------------------------------------------------

    SELECT
        lice_exceedances,
        exceedance_percentage
    INTO STRICT
        actual_exceedances,
        actual_percentage
    FROM aquainsight.v_annual_lice_summary
    WHERE year = 2025;

    IF actual_exceedances <> 1
       OR actual_percentage <> 33.33 THEN
        RAISE EXCEPTION
            'Annual exceedance statistics incorrect';
    END IF;

    RAISE NOTICE
        'PASS: Annual sea-lice summary';

END $$;


-- ============================================================
-- Check 4: Production-area statistics
-- ============================================================

DO $$
DECLARE
    actual_percentage NUMERIC;
BEGIN

    SELECT exceedance_percentage
    INTO STRICT actual_percentage
    FROM aquainsight.v_production_area_annual
    WHERE year = 2025
      AND production_area_id = 3;

    IF actual_percentage <> 50.00 THEN
        RAISE EXCEPTION
            'Production-area exceedance percentage incorrect: %',
            actual_percentage;
    END IF;

    RAISE NOTICE
        'PASS: Production-area statistics';

END $$;


-- ============================================================
-- Check 5: Data-quality statistics
-- ============================================================

DO $$
DECLARE
    actual_missing BIGINT;
    actual_conflicts BIGINT;
BEGIN

    SELECT
        missing_lice_measurements,
        reporting_conflicts
    INTO STRICT
        actual_missing,
        actual_conflicts
    FROM aquainsight.v_annual_data_quality
    WHERE year = 2025;

    IF actual_missing <> 1
       OR actual_conflicts <> 1 THEN
        RAISE EXCEPTION
            'Data-quality statistics incorrect';
    END IF;

    RAISE NOTICE
        'PASS: Annual data-quality statistics';

END $$;
