"""
AquaInsight — Pipeline Output Validation

Purpose:
    Determine whether existing Parquet outputs can
    be safely reused by the ETL orchestrator.

This module does not modify any files.
"""

from pathlib import Path

import pandas as pd


def check_pipeline_output(
    output_path: Path,
    reference_path: Path,
) -> bool:
    """
    Validate an existing pipeline output.

    Returns:
        True:
            Output exists and matches the reference.

        False:
            Output does not exist.

    Raises:
        FileNotFoundError:
            Reference dataset is missing.

        AssertionError:
            Existing output differs from reference.
    """

    output_path = Path(output_path)
    reference_path = Path(reference_path)

    # Reference must exist before validation.
    if not reference_path.is_file():
        raise FileNotFoundError(
            f"Reference dataset missing: {reference_path}"
        )

    # Missing output means rebuilding is required.
    if not output_path.is_file():
        print(f"REBUILD REQUIRED: {output_path.name}")
        return False

    print(f"Validating existing output: {output_path.name}")

    reference = pd.read_parquet(reference_path)
    output = pd.read_parquet(output_path)

    # Validate values, dtypes, column order and row order.
    pd.testing.assert_frame_equal(
        output.reset_index(drop=True),
        reference.reset_index(drop=True),
        check_dtype=True,
        check_exact=True,
    )

    print(
        f"PASS: {output_path.name} "
        f"({len(output):,} rows × {len(output.columns)} columns)"
    )

    return True
