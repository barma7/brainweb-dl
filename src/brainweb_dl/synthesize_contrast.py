"""Analytical MRI contrast synthesis from quantitative maps."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._brainweb import GenericPath, load_array, save_array
from .tissue_properties import TissuePropertyTable, load_tissue_properties

MapInput = GenericPath | NDArray


@dataclass(frozen=True)
class ContrastMaps:
    """Quantitative maps used for analytical contrast synthesis.

    Relaxation maps are expected in seconds. ``PD`` is an arbitrary normalized
    proton-density-like signal scale.
    """

    PD: MapInput | None = None
    T1: MapInput | None = None
    T2: MapInput | None = None
    T2s: MapInput | None = None
    affine: NDArray | None = None


@dataclass(frozen=True)
class ContrastSequence:
    """Analytical sequence parameters.

    ``TR`` and ``TE`` are in seconds. ``flip_angle`` is in degrees.
    """

    model: str
    TR: float | None = None
    TE: float = 0.0
    flip_angle: float | None = None


@dataclass(frozen=True)
class NoiseConfig:
    """White-matter calibrated magnitude-noise configuration."""

    snr: float
    fuzzy: MapInput
    tissue: str = "white_matter"
    fraction_threshold: float = 0.95
    rng: int | np.random.Generator | None = None
    tissue_properties: GenericPath | TissuePropertyTable | None = None


@dataclass
class SynthesizedContrastResult:
    """Synthesized contrast image with metadata needed for persistence."""

    data: NDArray
    affine: NDArray
    contrast: str
    sequence: dict[str, Any]
    required_maps: list[str]
    units: dict[str, str]
    metadata: dict[str, Any]


def synthesize_contrast(
    maps: ContrastMaps,
    sequence: ContrastSequence,
    contrast: str | None = None,
    noise: NoiseConfig | None = None,
) -> SynthesizedContrastResult:
    """Synthesize an analytical weighted magnitude image.

    Parameters
    ----------
    maps
        Quantitative maps. Required fields depend on the selected sequence
        model and contrast.
    sequence
        Analytical sequence parameters. TR and TE are seconds; flip angle is
        degrees.
    contrast
        Requested contrast label. Defaults from the sequence model when omitted.
    noise
        Optional Rician magnitude noise configuration.
    """
    model = _normalize_model(sequence.model)
    contrast_name = _normalize_contrast(contrast, model)
    required = _required_maps(model, contrast_name, sequence)
    loaded = _load_required_maps(maps, required)
    clean, model_name = _clean_signal(loaded.data, model, sequence)
    noise_metadata: dict[str, Any] = {"enabled": False}

    if noise is not None:
        noisy, noise_metadata = _add_rician_noise(clean, noise)
        data = noisy
    else:
        data = clean

    metadata = {
        "contrast": contrast_name,
        "sequence": _sequence_metadata(sequence, model),
        "required_maps": required,
        "units": _units_metadata(),
        "analytical_model": model_name,
        "noise": noise_metadata,
    }
    return SynthesizedContrastResult(
        data=np.asarray(data, dtype=np.float32),
        affine=loaded.affine,
        contrast=contrast_name,
        sequence=metadata["sequence"],
        required_maps=required,
        units=metadata["units"],
        metadata=metadata,
    )


def save_synthesized_contrast(
    result: SynthesizedContrastResult, path: GenericPath
) -> Path:
    """Save a synthesized contrast as NIfTI plus JSON sidecar metadata."""
    path_ = Path(path)
    save_array(result.data, result.affine, path_)
    _sidecar_path(path_).write_text(
        json.dumps(result.metadata, indent=2), encoding="utf-8"
    )
    return path_


@dataclass(frozen=True)
class _LoadedMaps:
    data: dict[str, NDArray]
    affine: NDArray


def _load_required_maps(maps: ContrastMaps, required: list[str]) -> _LoadedMaps:
    loaded: dict[str, NDArray] = {}
    path_affines: list[tuple[str, NDArray]] = []
    ref_shape: tuple[int, ...] | None = None

    for name in required:
        value = getattr(maps, name)
        if value is None:
            raise ValueError(f"Map {name} is required for this contrast model")
        data, affine, from_path = _load_map(value)
        if data.ndim != 3:
            raise ValueError(f"Map {name} must be a 3D array")
        if ref_shape is None:
            ref_shape = data.shape
        elif data.shape != ref_shape:
            raise ValueError(
                f"Map {name} shape {data.shape} does not match {ref_shape}"
            )
        loaded[name] = np.asarray(data, dtype=np.float32)
        if from_path:
            path_affines.append((name, affine))

    if path_affines:
        ref_name, affine = path_affines[0]
        for name, other in path_affines[1:]:
            if not np.allclose(other, affine):
                raise ValueError(
                    f"Map {name} affine does not match required map {ref_name}"
                )
        output_affine = affine
    elif maps.affine is not None:
        output_affine = np.asarray(maps.affine, dtype=np.float32)
    else:
        output_affine = np.eye(4, dtype=np.float32)

    return _LoadedMaps(data=loaded, affine=np.asarray(output_affine, dtype=np.float32))


def _load_map(value: MapInput) -> tuple[NDArray, NDArray, bool]:
    if isinstance(value, (str, os.PathLike)):
        data, affine = load_array(value)
        return np.asarray(data), np.asarray(affine, dtype=np.float32), True
    return np.asarray(value), np.eye(4, dtype=np.float32), False


def _clean_signal(
    maps: dict[str, NDArray], model: str, sequence: ContrastSequence
) -> tuple[NDArray, str]:
    if model == "spin_echo":
        return _spin_echo_signal(maps, sequence), "spin echo"
    if model == "spgr":
        return _spgr_signal(maps, sequence), "SPGR/FLASH"
    if model == "gre":
        return _gre_t2star_signal(maps, sequence), "gradient echo T2-star"
    raise ValueError(f"Unsupported sequence model {sequence.model!r}")


def _spin_echo_signal(maps: dict[str, NDArray], sequence: ContrastSequence) -> NDArray:
    tr = _require_positive(sequence.TR, "TR")
    te = _require_nonnegative(sequence.TE, "TE")
    pd = maps["PD"]
    t1 = maps["T1"]
    t2 = maps["T2"]
    signal = np.zeros_like(pd, dtype=np.float32)
    valid = (t1 > 0) & (t2 > 0)
    signal[valid] = (
        pd[valid]
        * (1.0 - np.exp(-tr / t1[valid]))
        * np.exp(-te / t2[valid])
    )
    return signal


def _spgr_signal(maps: dict[str, NDArray], sequence: ContrastSequence) -> NDArray:
    tr = _require_positive(sequence.TR, "TR")
    te = _require_nonnegative(sequence.TE, "TE")
    flip_angle = _require_value(sequence.flip_angle, "flip_angle")
    alpha = np.deg2rad(float(flip_angle))
    pd = maps["PD"]
    t1 = maps["T1"]
    signal = np.zeros_like(pd, dtype=np.float32)
    valid = t1 > 0
    e1 = np.exp(-tr / t1[valid])
    denominator = 1.0 - np.cos(alpha) * e1
    base = np.divide(
        np.sin(alpha) * (1.0 - e1),
        denominator,
        out=np.zeros_like(e1, dtype=np.float32),
        where=denominator != 0,
    )
    signal[valid] = pd[valid] * base
    if te > 0:
        t2s = maps["T2s"]
        decay_valid = valid & (t2s > 0)
        decayed = np.zeros_like(signal, dtype=np.float32)
        decayed[decay_valid] = signal[decay_valid] * np.exp(-te / t2s[decay_valid])
        signal = decayed
    return signal


def _gre_t2star_signal(
    maps: dict[str, NDArray], sequence: ContrastSequence
) -> NDArray:
    te = _require_nonnegative(sequence.TE, "TE")
    pd = maps["PD"]
    t2s = maps["T2s"]
    signal = np.zeros_like(pd, dtype=np.float32)
    valid = t2s > 0
    signal[valid] = pd[valid] * np.exp(-te / t2s[valid])
    return signal


def _add_rician_noise(
    clean: NDArray, noise: NoiseConfig
) -> tuple[NDArray, dict[str, Any]]:
    if noise.snr <= 0:
        raise ValueError("SNR must be positive")
    fuzzy = _load_fuzzy(noise.fuzzy, clean.shape)
    channel_idx = _tissue_channel_index(noise)
    if channel_idx >= fuzzy.shape[-1]:
        raise ValueError(f"Fuzzy segmentation does not contain {noise.tissue!r}")
    fractions = np.asarray(fuzzy[..., channel_idx], dtype=np.float32)
    if np.nanmax(fractions) > 1.0 or np.issubdtype(fuzzy.dtype, np.integer):
        fractions = fractions / 4095.0
    mask = fractions >= noise.fraction_threshold
    if not np.any(mask):
        raise ValueError(
            "White-matter SNR mask is empty; lower the threshold or check fuzzy input"
        )
    signal_ref = float(np.mean(clean[mask]))
    if signal_ref <= 0:
        raise ValueError("White-matter clean signal is not positive")
    sigma = signal_ref / float(noise.snr)
    rng = np.random.default_rng(noise.rng)
    real_noise = rng.normal(0.0, sigma, size=clean.shape)
    imag_noise = rng.normal(0.0, sigma, size=clean.shape)
    noisy = np.sqrt((clean + real_noise) ** 2 + imag_noise**2)
    metadata = {
        "enabled": True,
        "model": "Rician magnitude",
        "requested_snr": float(noise.snr),
        "snr_definition": (
            "mean clean magnitude signal in white-matter mask divided by sigma"
        ),
        "calibration_tissue": noise.tissue,
        "fraction_threshold": float(noise.fraction_threshold),
        "clean_calibration_signal": signal_ref,
        "sigma": float(sigma),
    }
    return np.asarray(noisy, dtype=np.float32), metadata


def _load_fuzzy(fuzzy: MapInput, shape: tuple[int, ...]) -> NDArray:
    data, _, _ = _load_map(fuzzy)
    if data.ndim != 4:
        raise ValueError("Fuzzy segmentation must be a 4D channel array")
    if data.shape[:3] != shape:
        raise ValueError(
            f"Fuzzy segmentation shape {data.shape[:3]} does not match {shape}"
        )
    return np.asarray(data)


def _tissue_channel_index(noise: NoiseConfig) -> int:
    table = (
        noise.tissue_properties
        if isinstance(noise.tissue_properties, TissuePropertyTable)
        else load_tissue_properties(noise.tissue_properties)
    )
    for idx, channel in enumerate(table.channels):
        if channel.name == noise.tissue:
            return idx
    raise ValueError(f"Tissue {noise.tissue!r} is not defined in metadata")


def _required_maps(
    model: str, contrast: str, sequence: ContrastSequence
) -> list[str]:
    te = _require_nonnegative(sequence.TE, "TE")
    if model == "spin_echo":
        if contrast not in {"T1w", "T2w"}:
            raise ValueError("Spin-echo synthesis supports T1w and T2w contrasts")
        return ["PD", "T1", "T2"]
    if model == "spgr":
        if contrast != "T1w":
            raise ValueError("SPGR/FLASH synthesis supports T1w contrast")
        return ["PD", "T1", "T2s"] if te > 0 else ["PD", "T1"]
    if model == "gre":
        if contrast != "T2*w":
            raise ValueError("GRE synthesis supports T2*w contrast")
        return ["PD", "T2s"]
    raise ValueError(f"Unsupported sequence model {model!r}")


def _normalize_model(model: str) -> str:
    normalized = model.lower().replace("-", "_").replace(" ", "_")
    lookup = {
        "se": "spin_echo",
        "spin_echo": "spin_echo",
        "spin_echo_t1w": "spin_echo",
        "spin_echo_t2w": "spin_echo",
        "spgr": "spgr",
        "flash": "spgr",
        "spoiled_gradient_echo": "spgr",
        "gre": "gre",
        "gradient_echo": "gre",
        "t2star_gre": "gre",
    }
    try:
        return lookup[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported sequence model {model!r}") from exc


def _normalize_contrast(contrast: str | None, model: str) -> str:
    if contrast is None:
        return "T2*w" if model == "gre" else "T1w"
    normalized = contrast.lower().replace("*", "star").replace("-", "")
    lookup = {
        "t1w": "T1w",
        "t1": "T1w",
        "t2w": "T2w",
        "t2": "T2w",
        "t2starw": "T2*w",
        "t2star": "T2*w",
        "t2sw": "T2*w",
        "t2s": "T2*w",
    }
    try:
        return lookup[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported contrast {contrast!r}") from exc


def _sequence_metadata(sequence: ContrastSequence, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "TR": sequence.TR,
        "TE": sequence.TE,
        "flip_angle": sequence.flip_angle,
        "TR_units": "s",
        "TE_units": "s",
        "flip_angle_units": "degrees",
    }


def _units_metadata() -> dict[str, str]:
    return {
        "PD": "arbitrary normalized proton-density-like scale",
        "T1": "s",
        "T2": "s",
        "T2s": "s",
        "TR": "s",
        "TE": "s",
        "flip_angle": "degrees",
        "output": "arbitrary magnitude signal",
    }


def _require_positive(value: float | None, name: str) -> float:
    value_ = _require_value(value, name)
    if value_ <= 0:
        raise ValueError(f"{name} must be positive")
    return value_


def _require_nonnegative(value: float | None, name: str) -> float:
    value_ = _require_value(value, name)
    if value_ < 0:
        raise ValueError(f"{name} must be non-negative")
    return value_


def _require_value(value: float | None, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required for this contrast model")
    return float(value)


def _sidecar_path(path: Path) -> Path:
    if path.name.endswith(".nii.gz"):
        return path.with_name(path.name[:-7] + ".json")
    return path.with_suffix(".json")
