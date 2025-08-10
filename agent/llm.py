import os
from typing import Dict, Any, List

LAST_PROVIDER = "unknown"

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai may be missing in fallback usage
    OpenAI = None  # type: ignore

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None  # type: ignore


def _fallback_tests(summary: Dict[str, Any], module_name: str) -> str:
    global LAST_PROVIDER
    LAST_PROVIDER = "fallback"
    functions: List[Dict[str, Any]] = summary.get("functions", [])
    has_top_level_input: bool = bool(summary.get("has_top_level_input"))
    lines: List[str] = []
    lines.append("import pytest")
    lines.append("")

    # If the module expects input() at top-level, provide CLI-style tests using monkeypatch
    if has_top_level_input:
        lines.append(f"def test_cli_positive(monkeypatch, capsys):")
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
        raises_list: List[str] = f.get("raises", [])
        required_args = [a for a in args if a not in defaults]

        # Basic smoke test calling the function with simple integers
        call_args_smoke = ", ".join(["1" for _ in required_args])
        lines.append(f"def test_{name}_smoke():")
        if len(required_args) == 0:
            lines.append(f"    _ = {module_name}.{name}()")
        else:
            lines.append(f"    _ = {module_name}.{name}({call_args_smoke})")
        lines.append("    assert True")
        lines.append("")

        # Simple error-path test for ZeroDivisionError if detected in AST
        if any("ZeroDivisionError" in r for r in raises_list):
            zero_args = ", ".join(["0" for _ in required_args]) or "0"
            lines.append(f"def test_{name}_zero_division():")
            lines.append("    with pytest.raises(ZeroDivisionError):")
            if len(required_args) == 0:
                lines.append(f"        _ = {module_name}.{name}()  # unlikely, but safe")
            else:
                lines.append(f"        _ = {module_name}.{name}({zero_args})")
            lines.append("")

    if not functions:
        lines.append("def test_module_imports():\n    assert True")
    return "\n".join(lines)


def generate_pytest_tests(summary: Dict[str, Any], source_code: str, module_name: str) -> str:
    global LAST_PROVIDER
    # 1) Prefer Gemini if GEMINI_API_KEY present
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai is not None:
        try:
            genai.configure(api_key=gemini_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
            system = (
                "You generate high-quality pytest tests. Cover units, integration, edge and error paths. "
                "Use only standard pytest style, no comments."
            )
            user = f"""
Summary (JSON):
{summary}

Source code:
\"\"\"{source_code}\"\"\"

Output only a pytest test module contents that imports the module under test and provides runnable tests.
"""
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content([system, user])
            text = (resp.text or "").strip()
            if text:
                LAST_PROVIDER = "gemini"
                return text
        except Exception:
            pass  # fall through to OpenAI or local

    # 2) Else try OpenAI if OPENAI_API_KEY present
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=openai_key)
            model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            system = (
                "You generate high-quality pytest tests. Cover units, integration, edge and error paths. "
                "Use only standard pytest style, no comments."
            )
            user = f"""
Summary (JSON):
{summary}

Source code:
\"\"\"{source_code}\"\"\"

Output only a pytest test module contents that imports the module under test and provides runnable tests.
"""
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            text = resp.choices[0].message.content.strip()
            if text:
                LAST_PROVIDER = "openai"
                return text
        except Exception:
            pass  # fall through to local

    # 3) Fallback local tests
    return _fallback_tests(summary, module_name)


