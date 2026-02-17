from __future__ import annotations

FS_PER_PS = 1000.0
NM_PER_M = 1e9


def fs_to_ps(value_fs: float) -> float:
    return value_fs / FS_PER_PS


def ps_to_fs(value_ps: float) -> float:
    return value_ps * FS_PER_PS


def nm_to_m(value_nm: float) -> float:
    return value_nm / NM_PER_M
