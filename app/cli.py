import argparse
import json
from pathlib import Path

from agent.generators.python_pytest import build_test_file
import agent.llm as llm
from agent.runner import run_pytest_with_coverage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to Python source file")
    parser.add_argument("--write-out", help="Write tests to this path")
    args = parser.parse_args()

    src_path = Path(args.file)
    code = src_path.read_text(encoding="utf-8")
    module_name = src_path.stem

    test_code = build_test_file(code, module_name, llm.generate_pytest_tests)
    if args.write_out:
        Path(args.write_out).write_text(test_code, encoding="utf-8")

    result = run_pytest_with_coverage(str(src_path), test_code)
    print(
        json.dumps(
            {
                "test_file_preview": test_code[:2000],
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "coverage_summary": result["coverage"].get("totals", {}),
                "llm_provider": llm.LAST_PROVIDER,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


