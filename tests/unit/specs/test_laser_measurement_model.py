import pytest

from cpa_sim.specs.mapping import map_laser_pulse_width_to_sim_width


@pytest.mark.unit
def test_autocorrelation_sech2_mapping_and_uncertainty_bounds() -> None:
    mapped = map_laser_pulse_width_to_sim_width(
        source_width_ps=2.0,
        source_measurement_type="autocorrelation_fwhm",
        assumed_pulse_shape="sech2",
        uncertainty_rel=0.1,
    )

    assert mapped.deconvolution_factor == pytest.approx(1.543)
    assert mapped.simulation_width_fs == pytest.approx((2.0 / 1.543) * 1_000.0)
    assert mapped.lower_bound_fs == pytest.approx(mapped.simulation_width_fs * 0.9)
    assert mapped.upper_bound_fs == pytest.approx(mapped.simulation_width_fs * 1.1)


@pytest.mark.unit
def test_intensity_fwhm_mapping_keeps_value_scale() -> None:
    mapped = map_laser_pulse_width_to_sim_width(
        source_width_ps=1.25,
        source_measurement_type="intensity_fwhm",
        assumed_pulse_shape="gaussian",
        uncertainty_rel=0.0,
    )

    assert mapped.deconvolution_factor == pytest.approx(1.0)
    assert mapped.simulation_width_fs == pytest.approx(1_250.0)


@pytest.mark.unit
def test_mapping_validates_inputs() -> None:
    with pytest.raises(ValueError, match="source_width_ps must be > 0"):
        map_laser_pulse_width_to_sim_width(
            source_width_ps=0.0,
            source_measurement_type="intensity_fwhm",
            assumed_pulse_shape="gaussian",
            uncertainty_rel=0.1,
        )

    with pytest.raises(ValueError, match="uncertainty_rel must be >= 0"):
        map_laser_pulse_width_to_sim_width(
            source_width_ps=1.0,
            source_measurement_type="intensity_fwhm",
            assumed_pulse_shape="gaussian",
            uncertainty_rel=-0.1,
        )
