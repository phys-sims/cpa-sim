from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PhaseOnlyDispersionCfg, TreacyGratingPairCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.physics.windowing import edge_energy_fraction
from cpa_sim.stages.free_space.treacy_grating import TreacyGratingStage


def _analytic_gaussian_state(
    *, n_samples: int = 64, dt_fs: float = 2.0, width_fs: float = 20.0
) -> LaserState:
    time_window_fs = dt_fs * (n_samples - 1)
    t = np.linspace(-0.5 * time_window_fs, 0.5 * time_window_fs, n_samples)
    field_t = np.exp(-0.5 * (t / width_fs) ** 2).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(n_samples, d=dt_fs))
    pulse = PulseState(
        grid=PulseGrid(
            t=t.tolist(),
            w=w.tolist(),
            dt=dt_fs,
            dw=float(w[1] - w[0]),
            center_wavelength_nm=1030.0,
        ),
        field_t=field_t,
        field_w=field_w,
        intensity_t=np.abs(field_t) ** 2,
        spectrum_w=np.abs(field_w) ** 2,
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={},
        metrics={},
        artifacts={},
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "cfg",
    [
        PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=10_000.0, tod_fs3=0.0),
        TreacyGratingPairCfg(
            name="stretcher",
            include_tod=False,
            override_gdd_fs2=10_000.0,
            override_tod_fs3=0.0,
        ),
    ],
)
def test_free_space_auto_window_reruns_for_targeted_stage(
    cfg: PhaseOnlyDispersionCfg | TreacyGratingPairCfg,
) -> None:
    initial = _analytic_gaussian_state()
    threshold = 1e-6
    edge_fraction = 0.05
    policy = {
        "cpa.auto_window.enabled": True,
        "cpa.auto_window.stages": ["stretcher"],
        "cpa.auto_window.print": False,
        "cpa.auto_window.edge_fraction": edge_fraction,
        "cpa.auto_window.max_edge_energy_fraction": threshold,
    }

    result = TreacyGratingStage(cfg).process(initial, policy=policy)
    out = result.state

    assert len(out.pulse.field_t) > len(initial.pulse.field_t)
    assert (
        edge_energy_fraction(np.asarray(out.pulse.intensity_t), edge_fraction=edge_fraction)
        <= threshold
    )
    assert "auto_window_events" in out.meta
    assert len(out.meta["auto_window_events"]) >= 1
    assert result.metrics["stretcher.auto_window_reruns"] >= 1


@pytest.mark.unit
def test_free_space_auto_window_disabled_keeps_grid_size() -> None:
    initial = _analytic_gaussian_state()
    policy = {
        "cpa.auto_window.enabled": False,
        "cpa.auto_window.stages": ["stretcher"],
        "cpa.auto_window.print": False,
        "cpa.auto_window.max_edge_energy_fraction": 1e-6,
    }

    result = TreacyGratingStage(
        PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=10_000.0, tod_fs3=0.0)
    ).process(initial, policy=policy)

    assert len(result.state.pulse.field_t) == len(initial.pulse.field_t)
