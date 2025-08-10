from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import List, Dict, Any
from radon.complexity import cc_visit


@dataclass
class FunctionSummary:
    name: str
    args: List[str]
    defaults: Dict[str, Any]
    raises: List[str]
    branches: int
    docstring: str | None


@dataclass
class FileSummary:
    functions: List[FunctionSummary]
    complexity: Dict[str, int]
    imports: List[str]
    has_top_level_input: bool


def summarize_python(code: str) -> FileSummary:
    tree = ast.parse(code)
    functions: List[FunctionSummary] = []
    imports: List[str] = []
    has_top_level_input = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", None)
            names = [n.name for n in node.names]
            imports.append(mod or ",".join(names))

        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            defaults: Dict[str, Any] = {}
            if node.args.defaults:
                for name, default in zip(args[-len(node.args.defaults) :], node.args.defaults):
                    if hasattr(ast, "unparse"):
                        defaults[name] = ast.unparse(default)  # type: ignore[attr-defined]
                    else:
                        defaults[name] = "default"

            raises: List[str] = []
            branches = 0
            for sub in ast.walk(node):
                if isinstance(sub, (ast.If, ast.Try, ast.For, ast.While, ast.With, ast.Match)):
                    branches += 1
                if isinstance(sub, ast.Raise):
                    try:
                        if hasattr(ast, "unparse"):
                            raises.append(ast.unparse(sub.exc))  # type: ignore[attr-defined]
                        else:
                            raises.append("Raise")
                    except Exception:
                        raises.append("Raise")

            functions.append(
                FunctionSummary(
                    name=node.name,
                    args=args,
                    defaults=defaults,
                    raises=raises,
                    branches=branches,
                    docstring=ast.get_docstring(node),
                )
            )

    # Detect top-level input() usage
    for node in getattr(tree, "body", []):
        call_node = None
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call_node = node.value
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call_node = node.value
        if call_node and isinstance(call_node.func, ast.Name) and call_node.func.id == "input":
            has_top_level_input = True

    complexity = {item.name: item.complexity for item in cc_visit(code)}
    return FileSummary(
        functions=functions,
        complexity=complexity,
        imports=list(set(imports)),
        has_top_level_input=has_top_level_input,
    )


