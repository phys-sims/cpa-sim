from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_example_modules_do_not_import_argparse() -> None:
    example_modules = [
        Path("src/cpa_sim/examples/simple_fiber_dispersion.py"),
        Path("src/cpa_sim/examples/fiber_amp_spm.py"),
        Path("src/cpa_sim/examples/wave_breaking_raman.py"),
        Path("src/cpa_sim/examples/end_to_end_1560nm.py"),
        Path("src/cpa_sim/examples/treacy_stage_validation.py"),
    ]
    for module_path in example_modules:
        source = module_path.read_text(encoding="utf-8")
        assert "import argparse" not in source
        assert "ArgumentParser(" not in source
