"""Structural evidence only. Never compile, import, or execute a submission."""

import ast

from pydantic import BaseModel, ConfigDict, Field


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    points: int = Field(ge=1, le=100)
    target: str = Field(default="", max_length=80)


def validate_rubric(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise ValueError("Provide 1–10 criteria")
    rows = [Criterion.model_validate(x) for x in value]
    if any(x.kind not in {"syntax", "function", "docstring", "no_imports"} for x in rows):
        raise ValueError("Unknown criterion")
    if any(x.kind in {"function", "docstring"} and not x.target.isidentifier() for x in rows):
        raise ValueError("Function criteria require an identifier target")
    if sum(x.points for x in rows) != 100:
        raise ValueError("Rubric points must sum to 100")
    return [x.model_dump() for x in rows]


def grade(source, rubric):
    try:
        tree = ast.parse(source)
        nodes = list(ast.walk(tree))
        if len(nodes) > 5000:
            raise ValueError("AST node limit exceeded")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return {
            "score": 0,
            "breakdown": [],
            "feedback": "Invalid or overly complex Python syntax",
            "mode": "ast-only",
        }
    functions = {
        n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    breakdown = []
    for row in rubric:
        kind, target = row["kind"], row["target"]
        passed = {
            "syntax": True,
            "function": target in functions,
            "docstring": target in functions and bool(ast.get_docstring(functions[target])),
            "no_imports": not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes),
        }[kind]
        breakdown.append({**row, "earned": row["points"] if passed else 0, "passed": passed})
    return {
        "score": sum(x["earned"] for x in breakdown),
        "breakdown": breakdown,
        "feedback": "Structural evidence only; runtime correctness is not tested.",
        "mode": "ast-only",
    }
