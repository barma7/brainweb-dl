"""Nasal-air correction for BrainWeb20 fuzzy segmentations."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Sequence

import numpy as np
from numpy.typing import NDArray

from ._brainweb import GenericPath, Segmentation, get_brainweb20, load_array, save_array
from .qmap import get_quantitative_map
from .synthesize_contrast import (
    ContrastMaps,
    ContrastSequence,
    NoiseConfig,
    save_synthesized_contrast,
    synthesize_contrast,
)

DEFAULT_T1W_SEQUENCE = ContrastSequence(
    model="flash",
    TR=0.025,
    TE=4e-3,
    flip_angle=20.0,
)
DEFAULT_T1W_SNR = 10.0


@dataclass(frozen=True)
class NasalAirCorrectionResult:
    """Paths and metadata for a corrected BrainWeb20 fuzzy derivative."""

    corrected_path: Path
    sidecar_path: Path
    source_fuzzy_path: Path
    t1w_path: Path
    paraside_mask_path: Path
    patched_voxels: int
    metadata: dict[str, Any]


def patch_fuzzy_with_air_mask(
    fuzzy: NDArray,
    mask: NDArray,
) -> NDArray:
    """Return a fuzzy copy with every nonzero PARASIDE voxel as background."""
    fuzzy_ = np.asarray(fuzzy)
    mask_ = np.asarray(mask)
    _validate_fuzzy_mask_geometry(fuzzy_, mask_)

    patched = fuzzy_.copy()
    air = _air_mask(mask_)
    background_value = _background_value(patched)
    patched[air, 0] = background_value
    patched[air, 1:] = 0
    return patched


def correct_fuzzy_nasal_air(
    subject: int,
    *,
    brainweb_dir: GenericPath | None = None,
    output: GenericPath,
    paraside_model: GenericPath,
    paraside_env: GenericPath | None = None,
    paraside_executable: GenericPath | None = None,
    sequence: ContrastSequence = DEFAULT_T1W_SEQUENCE,
    t1w_snr: float | None = DEFAULT_T1W_SNR,
    t1w_rng: int | np.random.Generator | None = None,
    keep_intermediates: bool = False,
    force: bool = False,
) -> NasalAirCorrectionResult:
    """Correct a BrainWeb20 fuzzy segmentation with PARASIDE nasal-air labels."""
    if paraside_env is None and paraside_executable is None:
        raise ValueError("Either paraside_env or paraside_executable is required")
    if paraside_env is not None and paraside_executable is not None:
        raise ValueError("Use either paraside_env or paraside_executable, not both")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_fuzzy_path = Path(
        get_brainweb20(
            subject,
            brainweb_dir=brainweb_dir,
            segmentation=Segmentation.FUZZY,
            force=force,
        )
    )
    t1w_path = _default_t1w_path(output_path)
    generate_t1w_for_paraside(
        source_fuzzy_path,
        t1w_path,
        sequence=sequence,
        snr=t1w_snr,
        rng=t1w_rng,
    )
    command = build_paraside_command(
        t1w_path,
        paraside_model,
        paraside_env=paraside_env,
        paraside_executable=paraside_executable,
    )
    run_paraside(command)
    paraside_mask_path = expected_paraside_output_path(t1w_path)
    if not paraside_mask_path.exists():
        raise FileNotFoundError(
            f"Expected PARASIDE segmentation was not found: {paraside_mask_path}"
        )

    fuzzy, fuzzy_affine = load_array(source_fuzzy_path)
    mask, mask_affine = load_array(paraside_mask_path)
    _validate_fuzzy_mask_geometry(fuzzy, mask, fuzzy_affine, mask_affine)
    patched = patch_fuzzy_with_air_mask(fuzzy, mask)
    patched_voxels = int(np.count_nonzero(_air_mask(mask)))
    metadata = _correction_metadata(
        source_fuzzy_path=source_fuzzy_path,
        corrected_path=output_path,
        t1w_path=t1w_path,
        paraside_mask_path=paraside_mask_path,
        paraside_model=paraside_model,
        paraside_env=paraside_env,
        paraside_executable=paraside_executable,
        command=command,
        patched_voxels=patched_voxels,
        sequence=sequence,
        t1w_snr=t1w_snr,
    )
    sidecar_path = save_corrected_fuzzy(patched, fuzzy_affine, output_path, metadata)

    if not keep_intermediates and t1w_path.exists():
        t1w_path.unlink()
        metadata["t1w_intermediate_retained"] = False
        sidecar_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return NasalAirCorrectionResult(
        corrected_path=output_path,
        sidecar_path=sidecar_path,
        source_fuzzy_path=source_fuzzy_path,
        t1w_path=t1w_path,
        paraside_mask_path=paraside_mask_path,
        patched_voxels=patched_voxels,
        metadata=metadata,
    )


def generate_t1w_for_paraside(
    fuzzy: GenericPath | NDArray,
    output: GenericPath,
    *,
    affine: NDArray | None = None,
    sequence: ContrastSequence = DEFAULT_T1W_SEQUENCE,
    field_strength: float = 3.0,
    snr: float | None = DEFAULT_T1W_SNR,
    rng: int | np.random.Generator | None = None,
) -> Path:
    """Generate a same-grid T1w image for PARASIDE from a fuzzy segmentation."""
    output_path = Path(output)
    if isinstance(fuzzy, (str, os.PathLike)):
        fuzzy_data, fuzzy_affine = load_array(fuzzy)
    else:
        fuzzy_data = np.asarray(fuzzy)
        fuzzy_affine = affine
    pd = get_quantitative_map(
        fuzzy_data,
        "PD_TOTAL",
        affine=fuzzy_affine,
        field_strength=field_strength,
    )
    t1 = get_quantitative_map(
        fuzzy_data,
        "T1",
        affine=fuzzy_affine,
        field_strength=field_strength,
    )
    t2s = None
    if sequence.TE is not None and sequence.TE > 0:
        t2s = get_quantitative_map(
            fuzzy_data,
            "T2s",
            affine=fuzzy_affine,
            field_strength=field_strength,
        )
    noise = None
    if snr is not None:
        noise = NoiseConfig(snr=snr, fuzzy=fuzzy_data, rng=rng)
    result = synthesize_contrast(
        ContrastMaps(
            PD=pd.data,
            T1=t1.data,
            T2s=t2s.data if t2s is not None else None,
            affine=pd.affine,
        ),
        sequence,
        contrast="T1w",
        noise=noise,
    )
    if result.data.shape != pd.data.shape:
        raise ValueError("Synthesized T1w shape does not match fuzzy spatial shape")
    if not np.allclose(result.affine, pd.affine):
        raise ValueError("Synthesized T1w affine does not match fuzzy affine")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_synthesized_contrast(result, output_path)
    return output_path


def build_paraside_command(
    input_path: GenericPath,
    model_path: GenericPath,
    *,
    paraside_env: GenericPath | None = None,
    paraside_executable: GenericPath | None = None,
) -> list[str]:
    """Build the external PARASIDE command without invoking a shell."""
    if paraside_env is None and paraside_executable is None:
        raise ValueError("Either paraside_env or paraside_executable is required")
    if paraside_env is not None and paraside_executable is not None:
        raise ValueError("Use either paraside_env or paraside_executable, not both")
    input_ = str(Path(input_path))
    model = str(Path(model_path))
    if paraside_executable is not None:
        return [str(Path(paraside_executable)), "--i", input_, "--m", model]
    conda_executable = os.environ.get("CONDA_EXE", "conda")
    return [
        conda_executable,
        "run",
        "--no-capture-output",
        "-p",
        str(Path(paraside_env)),
        "paraside",
        "--i",
        input_,
        "--m",
        model,
    ]


def run_paraside(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run PARASIDE and raise a clear error on failure."""
    try:
        return subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        details = "\n".join(
            part for part in [exc.stdout, exc.stderr] if part
        ).strip()
        message = f"PARASIDE command failed with exit code {exc.returncode}"
        if details:
            message = f"{message}: {details}"
        raise RuntimeError(message) from exc


def expected_paraside_output_path(input_path: GenericPath) -> Path:
    """Return the PARASIDE CLI output path for a single input NIfTI."""
    path = Path(input_path)
    name = path.name.split(".")[0]
    return path.parent / "paraside_output" / f"{name}_nose_segmentation.nii.gz"


def save_corrected_fuzzy(
    data: NDArray,
    affine: NDArray,
    path: GenericPath,
    metadata: dict[str, Any],
) -> Path:
    """Save corrected fuzzy data as NIfTI plus JSON sidecar."""
    path_ = Path(path)
    path_.parent.mkdir(parents=True, exist_ok=True)
    save_array(data, affine, path_)
    sidecar = _sidecar_path(path_)
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return sidecar


def _validate_fuzzy_mask_geometry(
    fuzzy: NDArray,
    mask: NDArray,
    fuzzy_affine: NDArray | None = None,
    mask_affine: NDArray | None = None,
    *,
    affine_tolerance: float = 1e-5,
) -> None:
    if fuzzy.ndim != 4:
        raise ValueError("Fuzzy segmentation must be a 4D channel array")
    if mask.ndim != 3:
        raise ValueError("PARASIDE mask must be a 3D label array")
    if fuzzy.shape[:3] != mask.shape:
        raise ValueError(
            f"PARASIDE mask shape {mask.shape} does not match fuzzy shape "
            f"{fuzzy.shape[:3]}"
        )
    if fuzzy_affine is not None and mask_affine is not None:
        if not np.allclose(fuzzy_affine, mask_affine, atol=affine_tolerance):
            raise ValueError("PARASIDE mask affine does not match fuzzy affine")


def _air_mask(mask: NDArray) -> NDArray:
    return np.asarray(mask) != 0


def _background_value(fuzzy: NDArray) -> float | int:
    if np.issubdtype(fuzzy.dtype, np.integer):
        return np.array(4095, dtype=fuzzy.dtype).item()
    return 1.0


def _correction_metadata(
    *,
    source_fuzzy_path: Path,
    corrected_path: Path,
    t1w_path: Path,
    paraside_mask_path: Path,
    paraside_model: GenericPath,
    paraside_env: GenericPath | None,
    paraside_executable: GenericPath | None,
    command: Sequence[str],
    patched_voxels: int,
    sequence: ContrastSequence,
    t1w_snr: float | None,
) -> dict[str, Any]:
    return {
        "method": "PARASIDE nasal-air correction",
        "source_fuzzy_path": str(source_fuzzy_path),
        "corrected_output_path": str(corrected_path),
        "t1w_intermediate_path": str(t1w_path),
        "t1w_intermediate_retained": True,
        "paraside_mask_path": str(paraside_mask_path),
        "paraside_model_path": str(Path(paraside_model)),
        "paraside_env_path": str(Path(paraside_env)) if paraside_env else None,
        "paraside_executable_path": (
            str(Path(paraside_executable)) if paraside_executable else None
        ),
        "paraside_command": [str(part) for part in command],
        "paraside_mask_rule": "mask != 0",
        "patched_voxels": int(patched_voxels),
        "affine_validation": "matched",
        "t1w_synthesis": {
            "model": sequence.model,
            "TR": sequence.TR,
            "TE": sequence.TE,
            "flip_angle": sequence.flip_angle,
            "TR_units": "s",
            "TE_units": "s",
            "flip_angle_units": "degrees",
            "contrast": "T1w",
            "snr": t1w_snr,
            "snr_definition": (
                "mean clean magnitude signal in white-matter mask divided by sigma"
                if t1w_snr is not None
                else None
            ),
        },
    }


def _default_t1w_path(output_path: Path) -> Path:
    return output_path.with_name(f"{_stem(output_path)}_paraside_T1w.nii.gz")


def _stem(path: Path) -> str:
    return path.name[:-7] if path.name.endswith(".nii.gz") else path.stem


def _sidecar_path(path: Path) -> Path:
    if path.name.endswith(".nii.gz"):
        return path.with_name(path.name[:-7] + ".json")
    return path.with_suffix(".json")
