from __future__ import annotations

import argparse
import inspect
import json
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from cpa_sim.reporting.pipeline_run import write_json
from cpa_sim.tuning.adapter import PipelineTuningAdapter
from cpa_sim.tuning.parameter_space import tuning_to_parameter_space
from cpa_sim.tuning.schema import TuneConfig


def _parse_bool(value: str) -> bool:
    parsed = value.strip().lower()
    if parsed in {"1", "true", "yes", "y", "on"}:
        return True
    if parsed in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("Expected a boolean value (true/false).")


def add_tune_subcommand(subparsers: Any) -> None:
    tune_parser = subparsers.add_parser("tune", help="Run optimization and fitting workflows")
    tune_subparsers = tune_parser.add_subparsers(dest="tune_command", required=True)

    run_parser = tune_subparsers.add_parser("run", help="Run schema-driven tuning")
    run_parser.add_argument("--config", required=True, help="Path to tuning YAML config")
    run_parser.add_argument(
        "--rerun-best-with-plots",
        type=_parse_bool,
        default=None,
        help="Override config.output.rerun_best_with_plots.",
    )


def run_tune_command(args: argparse.Namespace) -> int:
    if args.tune_command != "run":
        return 2

    with Path(args.config).open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    tune_cfg = TuneConfig.model_validate(payload)

    rerun_override = args.rerun_best_with_plots
    if rerun_override is not None:
        tune_cfg = tune_cfg.model_copy(
            update={
                "output": tune_cfg.output.model_copy(
                    update={"rerun_best_with_plots": rerun_override}
                )
            }
        )

    return _run_optimization(tune_cfg)


def _run_optimization(config: TuneConfig) -> int:
    out_dir = config.output.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter = PipelineTuningAdapter(config)
    parameter_space = tuning_to_parameter_space(config)

    ml = _import_ml_symbols()
    strategy = _build_strategy(ml["CMAESStrategy"], config, parameter_space)
    logger = _build_logger(ml["OptimizationLogger"], out_dir)
    evaluator = _build_evaluator(ml.get("SimulationEvaluator"), adapter)
    runner = _build_runner(ml["OptimizationRunner"], strategy, evaluator, logger, config)

    result = _run_runner(runner, config)

    best_point = _extract_best_point(result)
    best_pipeline = adapter.base_payload
    from cpa_sim.tuning.parameter_space import apply_parameter_values

    best_config_payload = apply_parameter_values(best_pipeline, best_point)
    runtime_payload = dict(best_config_payload.get("runtime", {}))
    runtime_payload["seed"] = config.execution.seed
    best_config_payload["runtime"] = runtime_payload

    best_config_path = out_dir / config.output.best_config_name
    best_config_path.write_text(
        yaml.safe_dump(best_config_payload, sort_keys=False), encoding="utf-8"
    )

    summary = {
        "best_parameters": best_point,
        "best_config_path": str(best_config_path),
    }
    write_json(out_dir / "metrics.json", summary)
    (out_dir / "artifacts.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if config.output.rerun_best_with_plots:
        rerun_cfg = config.model_copy(
            update={"execution": config.execution.model_copy(update={"emit_stage_plots": True})}
        )
        rerun_adapter = PipelineTuningAdapter(rerun_cfg)
        rerun_adapter.evaluate(best_point, seed=config.execution.seed)

    print(f"Tuning finished. Best config saved to {best_config_path}")
    return 0


def _import_ml_symbols() -> dict[str, Any]:
    try:
        ml_module = import_module("phys_sims_utils.ml")
        CMAESStrategy = getattr(ml_module, "CMAESStrategy")
        OptimizationLogger = getattr(ml_module, "OptimizationLogger")
        OptimizationRunner = getattr(ml_module, "OptimizationRunner")
        SimulationEvaluator = getattr(ml_module, "SimulationEvaluator", None)
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "tune run requires optional dependency 'phys-sims-utils[ml]'. "
            "Install with `pip install -e .[ml]`."
        ) from exc

    return {
        "OptimizationRunner": OptimizationRunner,
        "OptimizationLogger": OptimizationLogger,
        "CMAESStrategy": CMAESStrategy,
        "SimulationEvaluator": SimulationEvaluator,
    }


def _build_strategy(strategy_cls: type[Any], config: TuneConfig, parameter_space: Any) -> Any:
    kwargs = {
        "parameter_space": parameter_space,
        "max_evals": config.optimizer.max_evals,
        "sigma0": config.optimizer.sigma0,
        "population_size": config.optimizer.population_size,
    }
    return _instantiate_flexible(strategy_cls, kwargs)


def _build_logger(logger_cls: type[Any], out_dir: Path) -> Any:
    return _instantiate_flexible(logger_cls, {"out_dir": out_dir, "run_dir": out_dir})


def _build_evaluator(evaluator_cls: type[Any] | None, adapter: PipelineTuningAdapter) -> Any:
    if evaluator_cls is None:
        return adapter
    try:
        return evaluator_cls(adapter.evaluate)
    except TypeError:
        return _instantiate_flexible(
            evaluator_cls, {"evaluate_fn": adapter.evaluate, "fn": adapter.evaluate}
        )


def _build_runner(
    runner_cls: type[Any],
    strategy: Any,
    evaluator: Any,
    logger: Any,
    config: TuneConfig,
) -> Any:
    kwargs = {
        "strategy": strategy,
        "optimizer": strategy,
        "evaluator": evaluator,
        "logger": logger,
        "out_dir": config.output.out_dir,
        "max_evals": config.optimizer.max_evals,
    }
    return _instantiate_flexible(runner_cls, kwargs)


def _run_runner(runner: Any, config: TuneConfig) -> Any:
    for method_name in ("run", "optimize"):
        method = getattr(runner, method_name, None)
        if method is None:
            continue
        for kwargs in (
            {"max_evals": config.optimizer.max_evals},
            {"n_evals": config.optimizer.max_evals},
            {},
        ):
            try:
                return method(**kwargs)
            except TypeError:
                continue
    raise TypeError("Unable to run OptimizationRunner with supported method signatures.")


def _extract_best_point(result: Any) -> dict[str, float]:
    for key in ("best_parameters", "best_point", "x_best", "x"):
        value = getattr(result, key, None)
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
    if isinstance(result, dict):
        for key in ("best_parameters", "best_point", "x_best", "x"):
            value = result.get(key)
            if isinstance(value, dict):
                return {str(k): float(v) for k, v in value.items()}
    raise ValueError("Could not locate best parameters in optimization result.")


def _instantiate_flexible(cls: type[Any], kwargs: dict[str, Any]) -> Any:
    signature = inspect.signature(cls)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        filtered = {k: v for k, v in kwargs.items() if v is not None}
    else:
        accepted = set(signature.parameters)
        filtered = {k: v for k, v in kwargs.items() if k in accepted and v is not None}

    try:
        return cls(**filtered)
    except TypeError:
        if "parameter_space" in kwargs and not filtered:
            return cls(kwargs["parameter_space"])
        raise
