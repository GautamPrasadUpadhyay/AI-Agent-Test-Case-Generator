import os
import subprocess
import tempfile
import json
import pathlib


def run_pytest_with_coverage(src_path: str, test_code: str) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        module_name = pathlib.Path(src_path).stem

        # Copy source
        code = pathlib.Path(src_path).read_text(encoding="utf-8")
        (temp_path / f"{module_name}.py").write_text(code, encoding="utf-8")

        # Write tests
        (temp_path / f"test_{module_name}.py").write_text(test_code, encoding="utf-8")

        # Run pytest + coverage (Windows-friendly; no piping)
        run_cmd = "coverage run -m pytest -q"
        proc = subprocess.run(run_cmd, cwd=temp_path, shell=True, capture_output=True, text=True)

        # Export coverage JSON
        cov_proc = subprocess.run("coverage json -q", cwd=temp_path, shell=True, capture_output=True, text=True)

        coverage_json = {}
        cov_file = temp_path / "coverage.json"
        if cov_file.exists():
            try:
                coverage_json = json.loads(cov_file.read_text())
            except Exception:
                coverage_json = {}

        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "coverage": coverage_json,
        }


