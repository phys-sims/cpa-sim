import pytest

from cpa_sim.models import AmpCfg, PipelineConfig, PhaseOnlyDispersionCfg, ToyFiberAmpCfg
from cpa_sim.pipeline import run_pipeline


@pytest.mark.unit
def test_toy_fiber_amp_gain_only_scales_energy() -> None:
    baseline = run_pipeline(
        PipelineConfig(
            stages=[
                ToyFiberAmpCfg(name="toy_amp", gain_db=0.0, beta2_s2_per_m=0.0, gamma_w_inv_m=0.0)
            ]
        )
    )
    boosted = run_pipeline(
        PipelineConfig(
            stages=[
                ToyFiberAmpCfg(name="toy_amp", gain_db=6.0, beta2_s2_per_m=0.0, gamma_w_inv_m=0.0)
            ]
        )
    )

    baseline_energy = baseline.metrics["cpa.toy_amp.toy_amp.energy_out_au"]
    boosted_energy = boosted.metrics["cpa.toy_amp.toy_amp.energy_out_au"]
    gain_linear = 10 ** (6.0 / 10.0)

    assert boosted_energy == pytest.approx(baseline_energy * gain_linear, rel=2e-3)


@pytest.mark.unit
def test_toy_fiber_amp_spm_broadens_spectrum() -> None:
    no_spm = run_pipeline(
        PipelineConfig(
            amp=AmpCfg(gain_linear=1.0),
            stages=[ToyFiberAmpCfg(name="toy_amp", gain_db=0.0, gamma_w_inv_m=0.0, n_steps=10)],
        )
    )
    with_spm = run_pipeline(
        PipelineConfig(
            amp=AmpCfg(gain_linear=1.0),
            stages=[ToyFiberAmpCfg(name="toy_amp", gain_db=0.0, gamma_w_inv_m=3e-3, n_steps=10)],
        )
    )

    no_spm_bw = no_spm.metrics["cpa.toy_amp.toy_amp.bandwidth_out_rad_per_fs"]
    with_spm_bw = with_spm.metrics["cpa.toy_amp.toy_amp.bandwidth_out_rad_per_fs"]

    assert with_spm_bw > no_spm_bw


@pytest.mark.unit
def test_stretched_pulse_reduces_toy_amp_b_integral_proxy() -> None:
    direct = run_pipeline(
        PipelineConfig(
            stages=[ToyFiberAmpCfg(name="toy_amp", gain_db=10.0, gamma_w_inv_m=4e-3, n_steps=8)],
        )
    )

    stretched = run_pipeline(
        PipelineConfig(
            stages=[
                PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=4.0e5, tod_fs3=0.0),
                ToyFiberAmpCfg(name="toy_amp", gain_db=10.0, gamma_w_inv_m=4e-3, n_steps=8),
            ],
        )
    )

    direct_b = direct.metrics["cpa.toy_amp.toy_amp.b_integral_proxy_rad"]
    stretched_b = stretched.metrics["cpa.toy_amp.toy_amp.b_integral_proxy_rad"]

    assert stretched_b < direct_b
