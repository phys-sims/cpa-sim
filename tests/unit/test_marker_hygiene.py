from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _is_pytest_mark_unit(node: ast.AST) -> bool:
    """Return True when node is pytest.mark.unit or a call thereof."""
    if isinstance(node, ast.Call):
        return _is_pytest_mark_unit(node.func)

    if not isinstance(node, ast.Attribute):
        return False
    if node.attr != "unit":
        return False

    mark_node = node.value
    if not isinstance(mark_node, ast.Attribute) or mark_node.attr != "mark":
        return False

    pytest_node = mark_node.value
    return isinstance(pytest_node, ast.Name) and pytest_node.id == "pytest"


def _has_unit_marker(tree: ast.Module) -> bool:
    # Support module-level marker assignment: pytestmark = pytest.mark.unit
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in statement.targets
            ):
                if _is_pytest_mark_unit(statement.value):
                    return True
        if isinstance(statement, ast.AnnAssign):
            target = statement.target
            if isinstance(target, ast.Name) and target.id == "pytestmark" and statement.value:
                if _is_pytest_mark_unit(statement.value):
                    return True

    # Support decorator usage on tests/classes.
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if any(_is_pytest_mark_unit(decorator) for decorator in node.decorator_list):
            return True

    return False


@pytest.mark.unit
def test_each_unit_test_file_has_unit_marker() -> None:
    tests_unit_dir = Path(__file__).resolve().parent
    missing: list[str] = []

    for path in sorted(tests_unit_dir.rglob("test_*.py")):
        if path == Path(__file__).resolve():
            continue

        tree = ast.parse(path.read_text(), filename=path.as_posix())
        if not _has_unit_marker(tree):
            missing.append(path.relative_to(tests_unit_dir.parent.parent).as_posix())

    assert not missing, (
        "Each tests/unit/test_*.py file must include at least one real @pytest.mark.unit marker "
        "(decorator or pytestmark assignment). "
        f"Missing markers in: {', '.join(missing)}"
    )
