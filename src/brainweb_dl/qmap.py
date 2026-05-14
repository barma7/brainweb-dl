"""Quantitative map generation from BrainWeb fuzzy segmentations."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from ._brainweb import GenericPath, load_array, save_array
from .tissue_properties import TissuePropertyTable, load_tissue_properties

logger = logging.getLogger("brainweb_dl")

RELAXATION_PROPERTIES = {"T1", "T2", "T2s"}
SUPPORTED_PROPERTIES = {
    "VF",
    "VF_TOTAL",
    "PD",
    "PD_TOTAL",
    "T1",
    "T2",
    "T2s",
    "ADC",
    "chi",
}


@dataclass
class QuantitativeMapResult:
    """Quantitative map data with metadata needed for persistence."""

    data: NDArray
    affine: NDArray
    property: str
    units: str
    field_strength: float
    source_channels: list[str]
    metadata: dict[str, Any]


def get_quantitative_map(
    fuzzy: GenericPath | NDArray,
    property: str,
    *,
    affine: NDArray | None = None,
    field_strength: float = 3.0,
    tissue_properties: GenericPath | TissuePropertyTable | None = None,
    stochastic: bool = False,
    rng: int | np.random.Generator | None = None,
) -> QuantitativeMapResult:
    """Generate a BrainWeb20 quantitative map from fuzzy segmentation data."""
    property_name = _normalize_property(property)
    table = (
        tissue_properties
        if isinstance(tissue_properties, TissuePropertyTable)
        else load_tissue_properties(tissue_properties)
    )
    data, affine_ = _load_fuzzy(fuzzy, affine)
    fractions, channels = _align_fractions(data, table)
    rng_ = np.random.default_rng(rng)

    if property_name == "VF":
        result = fractions
        units = table.units["volume_fraction"]
    elif property_name == "VF_TOTAL":
        result = np.sum(fractions, axis=-1, dtype=np.float32)
        units = table.units["volume_fraction"]
    elif property_name == "PD":
        pd = _channel_array(channels, "proton_density")
        result = fractions * pd
        units = table.units["proton_density"]
    elif property_name == "PD_TOTAL":
        pd = _channel_array(channels, "proton_density")
        result = np.sum(fractions * pd, axis=-1, dtype=np.float32)
        units = table.units["proton_density"]
    elif property_name in RELAXATION_PROPERTIES:
        field_key = table.require_field(field_strength)
        result = _apparent_relaxation(
            fractions, channels, field_key, property_name, stochastic, rng_
        )
        units = "s"
    elif property_name == "ADC":
        result = _weighted_average(fractions, channels, "adc")
        units = table.units["ADC"]
    elif property_name == "chi":
        chi = _channel_array(channels, "chi")
        result = np.sum(fractions * chi, axis=-1, dtype=np.float32)
        units = table.units["chi"]
    else:
        raise ValueError(f"Unsupported quantitative property {property!r}")

    metadata = _metadata(
        table,
        property_name,
        units,
        field_strength,
        [channel.name for channel in channels],
        stochastic,
    )
    return QuantitativeMapResult(
        data=np.asarray(result, dtype=np.float32),
        affine=affine_,
        property=property_name,
        units=units,
        field_strength=float(field_strength),
        source_channels=[channel.name for channel in channels],
        metadata=metadata,
    )


def save_quantitative_map(result: QuantitativeMapResult, path: GenericPath) -> Path:
    """Save one quantitative-map result as NIfTI+JSON or HDF5."""
    path_ = Path(path)
    if _is_hdf5(path_):
        save_quantitative_maps([result], path_)
        return path_

    save_array(result.data, result.affine, path_)
    _sidecar_path(path_).write_text(
        json.dumps(result.metadata, indent=2), encoding="utf-8"
    )
    return path_


def save_quantitative_maps(
    results: Iterable[QuantitativeMapResult], path: GenericPath
) -> Path:
    """Save multiple quantitative-map results to one HDF5 file."""
    path_ = Path(path)
    if not _is_hdf5(path_):
        raise ValueError("Multiple quantitative maps can only be saved together as HDF5")
    import h5py

    with h5py.File(path_, "w") as h5:
        for result in results:
            group = h5.create_group(result.property)
            group.create_dataset("data", data=result.data, compression="gzip")
            group.create_dataset("affine", data=result.affine)
            group.attrs["metadata"] = json.dumps(result.metadata)
            group.attrs["units"] = result.units
    return path_


def _load_fuzzy(
    fuzzy: GenericPath | NDArray, affine: NDArray | None
) -> tuple[NDArray, NDArray]:
    if isinstance(fuzzy, (str, os.PathLike)):
        data, loaded_affine = load_array(fuzzy)
        affine_ = loaded_affine
    else:
        data = np.asarray(fuzzy)
        affine_ = np.eye(4, dtype=np.float32) if affine is None else np.asarray(affine)
    if data.ndim != 4:
        raise ValueError("Fuzzy segmentation must be a 4D channel array")
    return np.asarray(data), np.asarray(affine_, dtype=np.float32)


def _align_fractions(
    data: NDArray, table: TissuePropertyTable
) -> tuple[NDArray, tuple[Any, ...]]:
    if data.shape[-1] > len(table.channels):
        raise ValueError(
            f"Fuzzy segmentation has {data.shape[-1]} channels, but metadata defines "
            f"{len(table.channels)} channels"
        )
    if data.shape[-1] < len(table.channels):
        missing = [channel.name for channel in table.channels[data.shape[-1] :]]
        logger.warning("Fuzzy segmentation is missing known channels: %s", missing)
    channels = table.channels[: data.shape[-1]]
    fractions = np.asarray(data, dtype=np.float32)
    if np.issubdtype(data.dtype, np.integer) or np.nanmax(fractions) > 1.0:
        fractions = fractions / 4095.0
    return fractions, channels


def _apparent_relaxation(
    fractions: NDArray,
    channels: tuple[Any, ...],
    field_key: str,
    property_name: str,
    stochastic: bool,
    rng: np.random.Generator,
) -> NDArray:
    numerator = np.zeros(fractions.shape[:-1], dtype=np.float32)
    denominator = np.zeros(fractions.shape[:-1], dtype=np.float32)
    for idx, channel in enumerate(channels):
        prop = channel.fields.get(field_key, {}).get(property_name)
        if prop is None or prop.mean_ms <= 0:
            continue
        weight = fractions[..., idx] * float(channel.proton_density)
        if stochastic:
            values_ms = rng.normal(prop.mean_ms, prop.std_ms, size=weight.shape)
            values_ms = np.clip(values_ms, np.finfo(np.float32).tiny, None)
        else:
            values_ms = prop.mean_ms
        values_s = np.asarray(values_ms, dtype=np.float32) / 1000.0
        numerator += weight / values_s
        denominator += weight
    rate = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=np.float32),
        where=denominator > 0,
    )
    return np.divide(
        1.0,
        rate,
        out=np.zeros_like(rate, dtype=np.float32),
        where=rate > 0,
    )


def _weighted_average(
    fractions: NDArray, channels: tuple[Any, ...], attr: str
) -> NDArray:
    values = _channel_array(channels, attr)
    pd = _channel_array(channels, "proton_density")
    weights = fractions * pd
    numerator = np.sum(weights * values, axis=-1, dtype=np.float32)
    denominator = np.sum(weights, axis=-1, dtype=np.float32)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=np.float32),
        where=denominator > 0,
    )


def _channel_array(channels: tuple[Any, ...], attr: str) -> NDArray:
    return np.asarray([getattr(channel, attr) for channel in channels], dtype=np.float32)


def _metadata(
    table: TissuePropertyTable,
    property_name: str,
    units: str,
    field_strength: float,
    channels: list[str],
    stochastic: bool,
) -> dict[str, Any]:
    return {
        "dataset": table.dataset,
        "metadata_version": table.version,
        "property": property_name,
        "output_units": units,
        "source_units": table.units,
        "field_strength": float(field_strength),
        "field_strength_unit": table.field_strength_unit,
        "method": _method(property_name),
        "source_channels": channels,
        "source_property_file": table.source_path,
        "stochastic": stochastic,
    }


def _method(property_name: str) -> str:
    if property_name in RELAXATION_PROPERTIES:
        return "proton-density-weighted apparent rate"
    if property_name == "ADC":
        return "proton-density-weighted average"
    if property_name == "chi":
        return "volume-fraction-weighted sum"
    return "channel fraction"


def _normalize_property(property_name: str) -> str:
    normalized = property_name.replace("*", "s")
    lookup = {
        "vf": "VF",
        "volume_fraction": "VF",
        "vf_total": "VF_TOTAL",
        "volume_fraction_total": "VF_TOTAL",
        "pd": "PD",
        "pd_total": "PD_TOTAL",
        "proton_density": "PD",
        "proton_density_total": "PD_TOTAL",
        "t1": "T1",
        "t2": "T2",
        "t2s": "T2s",
        "adc": "ADC",
        "chi": "chi",
    }
    try:
        return lookup[normalized.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported quantitative property {property_name!r}") from exc


def _is_hdf5(path: Path) -> bool:
    return path.suffix.lower() in {".h5", ".hdf5"}


def _sidecar_path(path: Path) -> Path:
    if path.name.endswith(".nii.gz"):
        return path.with_name(path.name[:-7] + ".json")
    return path.with_suffix(".json")
