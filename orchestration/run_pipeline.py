"""
AquaInsight — Historical ETL Pipeline Orchestrator

Purpose:
    Coordinate historical CSV consolidation and data cleaning.

Behavior:
    - Validate required scripts
    - Validate existing outputs before execution
    - Reuse valid outputs
    - Generate missing outputs
    - Validate outputs after execution
    - Stop on errors

Safety:
    - Never intentionally replace a valid existing Parquet output
    - Never modify the original reference datasets
    - Never modify PostgreSQL
    - Never execute the PostgreSQL loader

Scope:
    Fixed historical dataset: 2015–2025
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))


from orchestration.pipeline_validation import check_pipeline_output
from orchestration.pipeline_executor import execute_stage


# ============================================================
# CONFIGURATION
# ============================================================

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"


# ------------------------------------------------------------
# Transformation scripts
# ------------------------------------------------------------

CONSOLIDATION_SCRIPT = (
    PROJECT_ROOT
    / "src"
    / "consolidate_fishhealth.py"
)

CLEANING_SCRIPT = (
    PROJECT_ROOT
    / "src"
    / "clean_fishhealth.py"
)


# ------------------------------------------------------------
# Historical consolidated dataset
# ------------------------------------------------------------

CONSOLIDATED_OUTPUT = (
    PROCESSED_DIR
    / "barentswatch_lice_2015_2025_rebuilt.parquet"
)

CONSOLIDATED_REFERENCE = (
    PROCESSED_DIR
    / "barentswatch_lice_2015_2025.parquet"
)


# ------------------------------------------------------------
# Historical cleaned dataset
# ------------------------------------------------------------

CLEANED_OUTPUT = (
    PROCESSED_DIR
    / "barentswatch_lice_pipeline_rebuilt_2015_2025.parquet"
)

CLEANED_REFERENCE = (
    PROCESSED_DIR
    / "barentswatch_lice_cleaned_2015_2025.parquet"
)


# ------------------------------------------------------------
# Derived outputs
# ------------------------------------------------------------

ANNUAL_OUTPUT = (
    PROCESSED_DIR
    / "annual_compliance_rebuilt_2015_2025.csv"
)

PLOT_OUTPUT = (
    OUTPUTS_DIR
    / "annual_lice_exceedance_rebuilt_2015_2025.png"
)


# ============================================================
# VALIDATE REQUIRED SCRIPTS
# ============================================================

def validate_pipeline_scripts():
    """
    Confirm that the required transformation scripts exist.

    This does not execute either script.
    """

    print("\nValidating pipeline scripts...")

    scripts = {
        "consolidation": CONSOLIDATION_SCRIPT,
        "cleaning": CLEANING_SCRIPT,
    }

    for stage, script in scripts.items():

        if not script.is_file():

            raise FileNotFoundError(
                f"Missing {stage} script: {script}"
            )

        print(
            f"PASS: {stage} -> {script.name}"
        )


# ============================================================
# CHECK EXISTING OUTPUTS
# ============================================================

def inspect_outputs():
    """
    Validate existing consolidated and cleaned datasets.

    Returns
    -------
    dict
        True  = output exists and matches reference
        False = output is missing

    Raises
    ------
    AssertionError
        If an existing output differs from its reference.

    Other errors may propagate from the validation module.
    """

    print("\nChecking existing pipeline outputs...")

    results = {}

    results["consolidation"] = check_pipeline_output(
        output_path=CONSOLIDATED_OUTPUT,
        reference_path=CONSOLIDATED_REFERENCE,
    )

    results["cleaning"] = check_pipeline_output(
        output_path=CLEANED_OUTPUT,
        reference_path=CLEANED_REFERENCE,
    )

    return results


# ============================================================
# STAGE 1: HISTORICAL CONSOLIDATION
# ============================================================

def run_consolidation(is_valid):
    """
    Generate the consolidated historical dataset if missing.

    Existing valid consolidated data is reused.
    """

    print("\nSTAGE 1: Historical consolidation")

    if is_valid:

        print(
            "SKIP: Existing consolidated dataset is valid"
        )

        return

    print(
        "RUN: Consolidating historical CSV files"
    )

    # Preserve the existing script-based execution.
    #
    # The consolidation module has not yet been updated
    # to require module-based execution.

    execute_stage(
        module="src.consolidate_fishhealth"
    )

    # --------------------------------------------------------
    # Validate reconstructed output
    # --------------------------------------------------------

    result = check_pipeline_output(
        output_path=CONSOLIDATED_OUTPUT,
        reference_path=CONSOLIDATED_REFERENCE,
    )

    if not result:

        raise RuntimeError(
            "Consolidation completed without producing "
            "its output"
        )

    print(
        "PASS: Consolidation completed and validated"
    )


# ============================================================
# STAGE 2: HISTORICAL DATA CLEANING
# ============================================================

def run_cleaning(is_valid):
    """
    Generate the cleaned analytical dataset if missing.

    Uses module-based Python execution to support imports
    from orchestration.atomic_writer.

    Existing valid cleaned data is reused.
    """

    print("\nSTAGE 2: Data cleaning")

    # --------------------------------------------------------
    # A. Skip valid existing output
    # --------------------------------------------------------

    if is_valid:

        print(
            "SKIP: Existing cleaned dataset is valid"
        )

        return

    # --------------------------------------------------------
    # B. Verify consolidated input
    # --------------------------------------------------------

    if not CONSOLIDATED_OUTPUT.is_file():

        raise FileNotFoundError(
            "Cannot clean data: consolidated input is missing"
        )

    print(
        "RUN: Cleaning historical dataset"
    )

    # --------------------------------------------------------
    # C. Execute cleaning using Python module mode
    # --------------------------------------------------------

    execute_stage(

        module="src.clean_fishhealth",

        arguments=[

            "--input",
            str(CONSOLIDATED_OUTPUT),

            "--reference",
            str(CLEANED_REFERENCE),

            "--output",
            str(CLEANED_OUTPUT),

            "--annual-output",
            str(ANNUAL_OUTPUT),

            "--plot-output",
            str(PLOT_OUTPUT),

        ],
    )

    # --------------------------------------------------------
    # D. Validate reconstructed output
    # --------------------------------------------------------

    result = check_pipeline_output(
        output_path=CLEANED_OUTPUT,
        reference_path=CLEANED_REFERENCE,
    )

    if not result:

        raise RuntimeError(
            "Cleaning completed without producing "
            "its output"
        )

    print(
        "PASS: Cleaning completed and validated"
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    """
    Execute the historical ETL orchestration.

    Workflow:

        1. Validate transformation scripts.
        2. Inspect existing consolidated dataset.
        3. Inspect existing cleaned dataset.
        4. Rebuild missing consolidated output.
        5. Rebuild missing cleaned output.
        6. Validate reconstructed outputs.

    PostgreSQL is never modified.
    """

    print("=" * 55)
    print("AquaInsight — Historical ETL Pipeline")
    print("=" * 55)

    # --------------------------------------------------------
    # STEP 1: Validate transformation scripts
    # --------------------------------------------------------

    validate_pipeline_scripts()

    # --------------------------------------------------------
    # STEP 2: Inspect existing outputs
    # --------------------------------------------------------

    status = inspect_outputs()

    # --------------------------------------------------------
    # STEP 3: Consolidation
    # --------------------------------------------------------

    run_consolidation(
        is_valid=status["consolidation"]
    )

    # --------------------------------------------------------
    # STEP 4: Cleaning
    # --------------------------------------------------------

    run_cleaning(
        is_valid=status["cleaning"]
    )

    # --------------------------------------------------------
    # STEP 5: Completion report
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("AQUAINSIGHT ETL PIPELINE COMPLETED")
    print("=" * 55)

    print("Consolidation: PASS")
    print("Cleaning: PASS")
    print("Database operations: NONE")


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
