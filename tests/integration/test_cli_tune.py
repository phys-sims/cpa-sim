from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_cli_tune_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "cpa_sim.cli", "tune", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "usage: cpa-sim tune" in proc.stdout
    assert "run" in proc.stdout


def _write_fake_ml(fake_pkg_root: Path) -> None:
    fake_ml = fake_pkg_root / "phys_sims_utils" / "ml"
    fake_ml.mkdir(parents=True)
    (fake_pkg_root / "phys_sims_utils" / "__init__.py").write_text("", encoding="utf-8")
    (fake_ml / "__init__.py").write_text(
        """
class Parameter:
    def __init__(self, name, path, lower, upper, transform=None):
        self.name = name
        self.path = path
        self.lower = lower
        self.upper = upper
        self.transform = transform


class ParameterSpace:
    def __init__(self, parameters):
        self.parameters = parameters


class EvalResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class SimulationEvaluator:
    def __init__(self, fn):
        self.fn = fn


class CMAESStrategy:
    def __init__(self, parameter_space, max_evals, sigma0, population_size=None):
        self.parameter_space = parameter_space
        self.max_evals = max_evals


class OptimizationLogger:
    def __init__(self, out_dir):
        self.out_dir = out_dir


class OptimizationRunner:
    def __init__(self, strategy, evaluator, logger, max_evals):
        self.strategy = strategy
        self.evaluator = evaluator
        self.logger = logger
        self.max_evals = max_evals

    def run(self, max_evals):
        p = self.strategy.parameter_space.parameters[0]
        candidate = {p.path: 0.5 * (p.lower + p.upper)}
        self.evaluator.fn(candidate)
        return {"best_parameters": candidate}
""",
        encoding="utf-8",
    )


def _run_tune_cli(*, tuning_config: Path, fake_pkg_root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{fake_pkg_root}{os.pathsep}{env.get('PYTHONPATH', '')}"

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cpa_sim.cli",
            "tune",
            "run",
            "--config",
            str(tuning_config),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.mark.integration
def test_cli_tune_run_saves_best_config(tmp_path: Path) -> None:
    fake_pkg_root = tmp_path / "fake_pkg"
    _write_fake_ml(fake_pkg_root)

    out_dir = tmp_path / "out"
    tuning_config = tmp_path / "tuning.yaml"
    tuning_config.write_text(
        """
base_pipeline_config: configs/examples/basic_cpa.yaml
parameters:
  - name: compressor_sep
    path: compressor.separation_um
    bounds: [100000.0, 400000.0]
objective:
  metric: cpa.metrics.summary.fwhm_fs
  direction: minimize
optimizer:
  max_evals: 2
execution:
  seed: 7
output:
  out_dir: PLACEHOLDER
""".replace("PLACEHOLDER", str(out_dir)),
        encoding="utf-8",
    )

    proc = _run_tune_cli(tuning_config=tuning_config, fake_pkg_root=fake_pkg_root)

    assert proc.returncode == 0, proc.stderr
    assert (out_dir / "best_config.yaml").exists()
    assert "Tuning finished." in proc.stdout


@pytest.mark.integration
def test_cli_tune_run_with_target_spectrum_csv(tmp_path: Path) -> None:
    fake_pkg_root = tmp_path / "fake_pkg"
    _write_fake_ml(fake_pkg_root)

    target_csv = tmp_path / "target_spectrum.csv"
    target_csv.write_text(
        "omega,signal\n-0.02,0.0\n0.0,1.0\n0.02,0.0\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out_spectral"
    tuning_config = tmp_path / "tuning_spectral.yaml"
    tuning_config.write_text(
        f"""
base_pipeline_config: configs/examples/basic_cpa.yaml
parameters:
  - name: compressor_sep
    path: compressor.separation_um
    bounds: [100000.0, 400000.0]
objective:
  kind: spectral_rmse
  target_csv: {target_csv}
  target_x_column: omega
  target_y_column: signal
  normalization: peak
optimizer:
  max_evals: 1
execution:
  seed: 7
output:
  out_dir: {out_dir}
""",
        encoding="utf-8",
    )

    proc = _run_tune_cli(tuning_config=tuning_config, fake_pkg_root=fake_pkg_root)

    assert proc.returncode == 0, proc.stderr
    assert (out_dir / "best_config.yaml").exists()
    assert "Tuning finished." in proc.stdout
