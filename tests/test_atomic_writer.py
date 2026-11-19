"""
AquaInsight — Atomic Parquet Writer Tests

Tests:
    1. Successful Parquet writing
    2. Exact data preservation
    3. Existing-file protection during write failure
    4. Temporary-file cleanup

These tests use pytest's temporary directories.

They do not modify historical datasets or PostgreSQL.
"""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from orchestration.atomic_writer import atomic_write_parquet


# ============================================================
# TEST 1: SUCCESSFUL ATOMIC WRITING
# ============================================================

def test_atomic_write_success(tmp_path: Path):
    """
    Verify that a DataFrame is saved correctly.

    tmp_path is a temporary directory provided by pytest.
    """

    output_file = tmp_path / "test_output.parquet"

    original_df = pd.DataFrame({
        "year": [2023, 2024, 2025],
        "locality_id": [1001, 1002, 1003],
        "adult_female_lice": [0.2, 0.5, 0.8],
    })

    atomic_write_parquet(
        original_df,
        output_file,
    )

    assert output_file.is_file()

    saved_df = pd.read_parquet(output_file)

    pd.testing.assert_frame_equal(
        original_df,
        saved_df,
        check_dtype=True,
        check_exact=True,
    )

    temporary_files = list(
        tmp_path.glob(".aquainsight_tmp_*")
    )

    assert temporary_files == []


# ============================================================
# TEST 2: EXISTING-FILE PROTECTION
# ============================================================

def test_atomic_write_failure_preserves_existing_file(
    tmp_path: Path,
):
    """
    Simulate a disk-writing failure.

    The existing destination must remain unchanged.
    """

    output_file = tmp_path / "test_output.parquet"

    original_df = pd.DataFrame({
        "year": [2024, 2025],
        "adult_female_lice": [0.2, 0.4],
    })

    replacement_df = pd.DataFrame({
        "year": [2024, 2025],
        "adult_female_lice": [9.9, 8.8],
    })

    atomic_write_parquet(
        original_df,
        output_file,
    )

    with patch.object(
        pd.DataFrame,
        "to_parquet",
        side_effect=OSError("Simulated disk write failure"),
    ):

        with pytest.raises(
            OSError,
            match="Simulated disk write failure",
        ):

            atomic_write_parquet(
                replacement_df,
                output_file,
            )

    saved_df = pd.read_parquet(output_file)

    pd.testing.assert_frame_equal(
        original_df,
        saved_df,
        check_dtype=True,
        check_exact=True,
    )

    temporary_files = list(
        tmp_path.glob(".aquainsight_tmp_*")
    )

    assert temporary_files == []


# ============================================================
# TEST 3: ATOMIC REPLACEMENT
# ============================================================

def test_atomic_write_replaces_existing_file(
    tmp_path: Path,
):
    """
    Verify that a successful atomic write replaces
    an existing destination with the new dataset.
    """

    output_file = tmp_path / "test_output.parquet"

    original_df = pd.DataFrame({
        "year": [2024],
        "adult_female_lice": [0.2],
    })

    replacement_df = pd.DataFrame({
        "year": [2025],
        "adult_female_lice": [0.8],
    })

    atomic_write_parquet(
        original_df,
        output_file,
    )

    atomic_write_parquet(
        replacement_df,
        output_file,
    )

    saved_df = pd.read_parquet(output_file)

    pd.testing.assert_frame_equal(
        replacement_df,
        saved_df,
        check_dtype=True,
        check_exact=True,
    )

    assert list(tmp_path.glob(".aquainsight_tmp_*")) == []
