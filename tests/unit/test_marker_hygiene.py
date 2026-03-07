from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_each_unit_test_file_has_unit_marker() -> None:
    missing: list[str] = []
    for path in sorted(Path("tests/unit").glob("**/test_*.py")):
        text = path.read_text()
        if "@pytest.mark.unit" not in text:
            missing.append(path.as_posix())

    assert not missing, (
        "Each tests/unit/test_*.py file must include at least one @pytest.mark.unit marker. "
        f"Missing markers in: {', '.join(missing)}"
    )
