"""
AquaInsight — Atomic Parquet Writer

Purpose:
    Write Parquet datasets safely using a temporary file.

Workflow:
    1. Create a temporary file.
    2. Write the DataFrame.
    3. Reload and validate the temporary file.
    4. Atomically replace the destination.
    5. Remove temporary files if an error occurs.
"""

import os
import tempfile
from pathlib import Path

import pandas as pd


def atomic_write_parquet(df: pd.DataFrame, output_path: Path):
    """
    Safely write a DataFrame to a Parquet file.

    The destination is replaced only after the temporary
    Parquet file has passed validation.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        # Create temporary file in the destination directory.
        # This helps ensure replacement happens on one filesystem.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".parquet",
            prefix=".aquainsight_tmp_",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        # Write the dataset to the temporary file.
        df.to_parquet(
            temporary_path,
            engine="pyarrow",
            index=False,
        )

        # Reload the temporary file.
        reloaded = pd.read_parquet(temporary_path)

        # Verify that saving preserved the dataset.
        pd.testing.assert_frame_equal(
            df.reset_index(drop=True),
            reloaded.reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
        )

        # Replace destination only after validation succeeds.
        os.replace(temporary_path, output_path)

        print(f"PASS: Atomically saved {output_path.name}")

    finally:
        # Clean up temporary files if writing fails.
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
