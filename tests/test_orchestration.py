"""
AquaInsight — ETL Orchestration Tests

Purpose:
    Verify orchestration control flow without executing
    historical transformations or modifying PostgreSQL.
"""

from unittest.mock import patch

import orchestration.run_pipeline as pipeline


def test_skip_valid_outputs():
    """
    When both existing outputs are valid,
    neither transformation should execute.
    """

    with (
        patch.object(
            pipeline,
            "validate_pipeline_scripts",
        ),
        patch.object(
            pipeline,
            "inspect_outputs",
            return_value={
                "consolidation": True,
                "cleaning": True,
            },
        ),
        patch.object(
            pipeline,
            "execute_stage",
        ) as executor,
    ):

        pipeline.main()

        # No transformation should execute.
        executor.assert_not_called()
def test_rebuild_missing_outputs():
    """
    Verify that the orchestrator requests both
    transformation stages when outputs are missing.

    All transformation functions are mocked, so
    no historical datasets are modified.
    """

    with (
        patch.object(
            pipeline,
            "validate_pipeline_scripts",
        ) as validate_scripts,

        patch.object(
            pipeline,
            "inspect_outputs",
            return_value={
                "consolidation": False,
                "cleaning": False,
            },
        ) as inspect,

        patch.object(
            pipeline,
            "run_consolidation",
        ) as consolidation,

        patch.object(
            pipeline,
            "run_cleaning",
        ) as cleaning,
    ):

        pipeline.main()

        validate_scripts.assert_called_once_with()

        inspect.assert_called_once_with()

        consolidation.assert_called_once_with(
            is_valid=False
        )

        cleaning.assert_called_once_with(
            is_valid=False
        )
        
# ============================================================
# TEST 3: CONSOLIDATION FAILURE HANDLING
# ============================================================

def test_consolidation_failure_stops_pipeline():
    """
    If consolidation fails, the orchestrator must stop.

    Cleaning must not execute.
    """

    import subprocess
    import pytest

    simulated_error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["python", "-m", "src.consolidate_fishhealth"],
    )

    with (
        patch.object(
            pipeline,
            "validate_pipeline_scripts",
        ),
        patch.object(
            pipeline,
            "inspect_outputs",
            return_value={
                "consolidation": False,
                "cleaning": False,
            },
        ),
        patch.object(
            pipeline,
            "execute_stage",
            side_effect=simulated_error,
        ) as executor,
    ):

        with pytest.raises(
            subprocess.CalledProcessError
        ) as error:

            pipeline.main()

        assert error.value.returncode == 1

        executor.assert_called_once_with(
            module="src.consolidate_fishhealth"
        )


# ============================================================
# TEST 4: CLEANING FAILURE HANDLING
# ============================================================

def test_cleaning_failure_stops_pipeline():
    """
    If cleaning fails, the orchestrator must stop.

    It must not report successful completion.
    """

    import subprocess
    import pytest

    simulated_error = subprocess.CalledProcessError(
        returncode=2,
        cmd=["python", "-m", "src.clean_fishhealth"],
    )

    with (
        patch.object(
            pipeline,
            "validate_pipeline_scripts",
        ),
        patch.object(
            pipeline,
            "inspect_outputs",
            return_value={
                "consolidation": True,
                "cleaning": False,
            },
        ),
        patch.object(
            pipeline,
            "CONSOLIDATED_OUTPUT",
            **{"is_file.return_value": True},
        ),
        patch.object(
            pipeline,
            "execute_stage",
            side_effect=simulated_error,
        ) as executor,
    ):

        with pytest.raises(
            subprocess.CalledProcessError
        ) as error:

            pipeline.main()

        assert error.value.returncode == 2

        executor.assert_called_once()

        assert (
            executor.call_args.kwargs["module"]
            == "src.clean_fishhealth"
        )
