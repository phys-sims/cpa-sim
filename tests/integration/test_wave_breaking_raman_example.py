from pathlib import Path

import pytest

from cpa_sim.examples.wave_breaking_raman import run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_wave_breaking_raman_example_emits_expected_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    outputs = run_example(
        out_dir=tmp_path,
        n_samples=1024,
        z_saves=48,
        raman_model="blowwood",
    )

    assert set(outputs) == {
        "z_traces_npz",
        "wavelength_linear",
        "wavelength_log",
        "delay_linear",
        "delay_log",
    }

    assert outputs["z_traces_npz"].name == "wave_breaking_raman_z_traces.npz"
    assert outputs["z_traces_npz"].suffix == ".npz"
    for key in ("wavelength_linear", "wavelength_log", "delay_linear", "delay_log"):
        assert outputs[key].suffix == ".png"

    for path in outputs.values():
        assert path.exists(), f"Expected artifact at {path}."
        assert path.stat().st_size > 0
