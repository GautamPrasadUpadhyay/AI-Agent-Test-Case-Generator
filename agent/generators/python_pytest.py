from agent.analysis import summarize_python
import re
from typing import Dict, Any, List


def _extract_code_from_markdown(text: str) -> str:
    # Pull python code blocks if present, otherwise return raw text
    if "```" in text:
        blocks = re.findall(r"```(?:\w+)?\s*([\s\S]*?)```", text)
        if blocks:
            return "\n\n".join(blocks)
    return text


def _sanitize_tests(text: str, module_name: str) -> str:
    code = _extract_code_from_markdown(text)
    # Remove accidental markdown remnants and stray language hints
    code = re.sub(r"^\s*python\s*$", "", code, flags=re.IGNORECASE | re.MULTILINE)
    code = code.replace("```", "")
    # Remove stray markdown separators
    code = re.sub(r"^\s*---\s*$", "", code, flags=re.MULTILINE)
    # Normalize common placeholder module names
    code = code.replace("my_module", module_name)
    code = code.replace("module_under_test", module_name)
    code = code.replace("under_test", module_name)
    # Rewrite imports that incorrectly use a generic name like 'module'
    code = re.sub(rf"(?m)^(\s*from\s+)module(\s+import\b)", rf"\1{module_name}\2", code)
    code = re.sub(rf"(?m)^(\s*import\s+)module(\b)", rf"\1{module_name}\2", code)
    return code.strip()


def _simple_fallback_tests(summary: Dict[str, Any], module_name: str) -> str:
    functions: List[Dict[str, Any]] = summary.get("functions", [])
    has_top_level_input: bool = bool(summary.get("has_top_level_input"))
    lines: List[str] = []
    lines.append("import pytest")
    lines.append("")
    if has_top_level_input:
        lines.append("def test_cli_positive(monkeypatch, capsys):")
        lines.append("    inputs = iter(['10', '5'])")
        lines.append("    monkeypatch.setattr('builtins.input', lambda _: next(inputs))")
        lines.append(f"    import importlib, {module_name} as m")
        lines.append("    importlib.reload(m)")
        lines.append("    captured = capsys.readouterr()")
        lines.append("    assert captured.out.strip() != ''")
        lines.append("")
    for f in functions:
        name = f.get("name")
        args = f.get("args", [])
        defaults = f.get("defaults", {})
        required = [a for a in args if a not in defaults]
        call_args = ", ".join(["1" for _ in required])
        lines.append(f"def test_{name}_smoke():")
        if required:
            lines.append(f"    _ = {module_name}.{name}({call_args})")
        else:
            lines.append(f"    _ = {module_name}.{name}()")
        lines.append("    assert True")
        lines.append("")
    if not functions and not has_top_level_input:
        lines.append("def test_script_runs(capsys):")
        lines.append(f"    import importlib, {module_name} as m")
        lines.append("    importlib.reload(m)")
        lines.append("    captured = capsys.readouterr()")
        lines.append("    assert captured.out.strip() != ''")
        lines.append("")
    code = "\n".join(lines)
    if f"import {module_name}" not in code and f"from {module_name}" not in code:
        code = f"import {module_name}\n\n" + code
    return code


def build_test_file(source_code: str, module_name: str, llm_generate) -> str:
    summary = summarize_python(source_code)
    summary_dict = {
        "imports": summary.imports,
        "complexity": summary.complexity,
        "functions": [
            {
                "name": f.name,
                "args": f.args,
                "defaults": f.defaults,
                "raises": f.raises,
                "branches": f.branches,
                "docstring": f.docstring,
            }
            for f in summary.functions
        ],
        "has_top_level_input": summary.has_top_level_input,
    }
    # If there are no functions, prefer robust script/CLI tests and skip the LLM entirely
    if not summary_dict["functions"]:
        return _simple_fallback_tests(summary_dict, module_name)

    tests_raw = llm_generate(summary_dict, source_code, module_name)
    tests = _sanitize_tests(tests_raw, module_name)
    # If tests try to import names that do not exist in the module, fall back to safe tests
    defined_names = {f["name"] for f in summary_dict["functions"]}
    missing_ref = False
    for m in re.finditer(rf"from\s+{re.escape(module_name)}\s+import\s+([^\n]+)", tests):
        imported = {name.strip() for name in re.split(r",|\s+", m.group(1)) if name.strip()}
        if not imported.issubset(defined_names):
            missing_ref = True
            break
    if missing_ref:
        tests = _simple_fallback_tests(summary_dict, module_name)
    if f"import {module_name}" not in tests and f"from {module_name}" not in tests:
        tests = f"import {module_name}\n\n" + tests
    return tests


