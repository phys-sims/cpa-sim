import pytest

from cpa_sim.models import (
    PhaseOnlyDispersionCfg,
    PipelineConfig,
    SimpleGainCfg,
    ToyFiberAmpCfg,
)
from cpa_sim.pipeline import run_pipeline


@pytest.mark.unit
def test_toy_fiber_amp_hits_target_average_power() -> None:
    target_power_w = 0.25
    result = run_pipeline(
        PipelineConfig(
            stages=[
                ToyFiberAmpCfg(
                    name="toy_amp",
                    amp_power_w=target_power_w,
                    beta2_s2_per_m=0.0,
                    gamma_w_inv_m=0.0,
                )
            ]
        )
    )

    assert result.metrics["cpa.toy_amp.toy_amp.power_out_avg_w"] == pytest.approx(
        target_power_w, rel=2e-3
    )


@pytest.mark.unit
def test_toy_fiber_amp_loss_compensation_still_hits_target_average_power() -> None:
    target_power_w = 0.1
    no_loss = run_pipeline(
        PipelineConfig(
            stages=[
                ToyFiberAmpCfg(
                    name="toy_amp",
                    amp_power_w=target_power_w,
                    gamma_w_inv_m=0.0,
                    loss_db_per_m=0.0,
                    length_m=2.0,
                )
            ]
        )
    )
    with_loss = run_pipeline(
        PipelineConfig(
            stages=[
                ToyFiberAmpCfg(
                    name="toy_amp",
                    amp_power_w=target_power_w,
                    gamma_w_inv_m=0.0,
                    loss_db_per_m=0.5,
                    length_m=2.0,
                )
            ]
        )
    )

    assert with_loss.metrics["cpa.toy_amp.toy_amp.power_out_avg_w"] == pytest.approx(
        target_power_w, rel=2e-3
    )
    assert with_loss.metrics["cpa.toy_amp.toy_amp.gain_db"] == pytest.approx(
        no_loss.metrics["cpa.toy_amp.toy_amp.gain_db"] + 1.0,
        abs=1e-9,
    )


@pytest.mark.unit
def test_toy_fiber_amp_spm_broadens_spectrum() -> None:
    no_spm = run_pipeline(
        PipelineConfig(
            amp=SimpleGainCfg(gain_linear=1.0),
            stages=[
                ToyFiberAmpCfg(name="toy_amp", amp_power_w=0.05, gamma_w_inv_m=0.0, n_steps=10)
            ],
        )
    )
    with_spm = run_pipeline(
        PipelineConfig(
            amp=SimpleGainCfg(gain_linear=1.0),
            stages=[
                ToyFiberAmpCfg(name="toy_amp", amp_power_w=0.05, gamma_w_inv_m=3e-3, n_steps=10)
            ],
        )
    )

    no_spm_bw = no_spm.metrics["cpa.toy_amp.toy_amp.bandwidth_out_rad_per_fs"]
    with_spm_bw = with_spm.metrics["cpa.toy_amp.toy_amp.bandwidth_out_rad_per_fs"]

    assert with_spm_bw > no_spm_bw


@pytest.mark.unit
def test_stretched_pulse_reduces_toy_amp_b_integral_proxy() -> None:
    direct = run_pipeline(
        PipelineConfig(
            stages=[ToyFiberAmpCfg(name="toy_amp", amp_power_w=0.4, gamma_w_inv_m=4e-3, n_steps=8)],
        )
    )

    stretched = run_pipeline(
        PipelineConfig(
            stages=[
                PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=4.0e5, tod_fs3=0.0),
                ToyFiberAmpCfg(name="toy_amp", amp_power_w=0.4, gamma_w_inv_m=4e-3, n_steps=8),
            ],
        )
    )

    direct_b = direct.metrics["cpa.toy_amp.toy_amp.b_integral_proxy_rad"]
    stretched_b = stretched.metrics["cpa.toy_amp.toy_amp.b_integral_proxy_rad"]

    assert stretched_b < direct_b
