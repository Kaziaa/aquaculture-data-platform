"""
AquaInsight — Pipeline Stage Executor

Purpose:
    Execute Python pipeline stages using either:
    1. Script-based execution
    2. Module-based execution

Features:
    - Validate script or module input
    - Use the active Python interpreter
    - Execute from the project root
    - Detect failures using process exit codes
"""

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def execute_stage(
    script_path=None,
    arguments=None,
    module=None,
):
    """
    Execute a Python pipeline stage.

    Parameters
    ----------
    script_path : Path or str, optional
        Path to a Python script.

    arguments : list, optional
        Command-line arguments.

    module : str, optional
        Python module name, for example:
        "src.clean_fishhealth"

    Exactly one of script_path or module must be provided.

    Raises
    ------
    ValueError
        If both or neither execution methods are supplied.

    FileNotFoundError
        If the script does not exist.

    subprocess.CalledProcessError
        If execution fails.
    """

    if (script_path is None) == (module is None):
        raise ValueError(
            "Provide exactly one of script_path or module"
        )

    if arguments is None:
        arguments = []

    if module is not None:

        if not isinstance(module, str) or not module.strip():
            raise ValueError("Module name must be a nonempty string")

        command = [
            sys.executable,
            "-m",
            module,
            *arguments,
        ]

        stage_name = module

    else:

        script_path = Path(script_path).resolve()

        if not script_path.is_file():
            raise FileNotFoundError(
                f"Pipeline script not found: {script_path}"
            )

        command = [
            sys.executable,
            str(script_path),
            *arguments,
        ]

        stage_name = script_path.name

    print(
        f"\nExecuting pipeline stage: {stage_name}",
        flush=True,
    )

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )

    print(
        f"PASS: {stage_name} completed successfully",
        flush=True,
    )
