"""Structured BrainWeb tissue-property metadata."""

from __future__ import annotations

from dataclasses import dataclass
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

GenericPath = str | Path


@dataclass(frozen=True)
class RelaxationProperty:
    """Relaxation property statistics stored in milliseconds."""

    mean_ms: float
    std_ms: float = 0.0
    provisional: bool = False


@dataclass(frozen=True)
class TissueChannel:
    """One BrainWeb tissue channel and its quantitative properties."""

    name: str
    label: int
    download_alias: str
    proton_density: float
    adc: float
    chi: float
    fields: dict[str, dict[str, RelaxationProperty]]
    provisional: bool = False


@dataclass(frozen=True)
class TissuePropertyTable:
    """Validated BrainWeb tissue-property table."""

    dataset: str
    version: int
    field_strength_unit: str
    units: dict[str, str]
    channels: tuple[TissueChannel, ...]
    source_path: str

    def field_key(self, field_strength: float | int | str) -> str:
        """Normalize a field-strength value to the JSON key convention."""
        try:
            return f"{float(field_strength):.1f}"
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid field strength {field_strength!r}") from exc

    def require_field(self, field_strength: float | int | str) -> str:
        """Return a field key or raise when no channel provides it."""
        key = self.field_key(field_strength)
        if not any(key in channel.fields for channel in self.channels):
            raise ValueError(
                f"Field strength {key} {self.field_strength_unit} is not available"
            )
        return key


class BrainWebTissueProperties:
    """Packaged structured tissue-property files."""

    v2: Path = files("brainweb_dl.data") / "brainweb20_tissue_properties.json"  # type: ignore


def load_tissue_properties(path: GenericPath | None = None) -> TissuePropertyTable:
    """Load and validate BrainWeb tissue-property JSON metadata."""
    source = Path(path) if path is not None else BrainWebTissueProperties.v2
    with source.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return _parse_tissue_properties(raw, str(source))


def _parse_tissue_properties(raw: dict[str, Any], source_path: str) -> TissuePropertyTable:
    required_top = {
        "dataset",
        "version",
        "field_strength_unit",
        "units",
        "channels",
    }
    missing = required_top - raw.keys()
    if missing:
        raise ValueError(f"Missing tissue-property fields: {sorted(missing)}")

    units = raw["units"]
    if not isinstance(units, dict):
        raise ValueError("Tissue-property units must be a mapping")

    channels_raw = raw["channels"]
    if not isinstance(channels_raw, list) or not channels_raw:
        raise ValueError("Tissue-property channels must be a non-empty list")

    channels: list[TissueChannel] = []
    seen_labels: set[int] = set()
    for idx, item in enumerate(channels_raw):
        channel = _parse_channel(item, idx)
        if channel.label in seen_labels:
            raise ValueError(f"Duplicate tissue label {channel.label}")
        seen_labels.add(channel.label)
        channels.append(channel)

    labels = [channel.label for channel in channels]
    if labels != sorted(labels):
        raise ValueError("Tissue channels must be ordered by label")

    return TissuePropertyTable(
        dataset=str(raw["dataset"]),
        version=int(raw["version"]),
        field_strength_unit=str(raw["field_strength_unit"]),
        units={str(k): str(v) for k, v in units.items()},
        channels=tuple(channels),
        source_path=source_path,
    )


def _parse_channel(raw: dict[str, Any], idx: int) -> TissueChannel:
    required = {
        "name",
        "label",
        "download_alias",
        "proton_density",
        "ADC",
        "chi",
        "fields",
    }
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Channel {idx} missing fields: {sorted(missing)}")

    fields_raw = raw["fields"]
    if not isinstance(fields_raw, dict) or not fields_raw:
        raise ValueError(f"Channel {idx} fields must be a non-empty mapping")

    fields: dict[str, dict[str, RelaxationProperty]] = {}
    for field_key, properties in fields_raw.items():
        if not isinstance(properties, dict):
            raise ValueError(f"Channel {idx} field {field_key} must be a mapping")
        fields[str(float(field_key))] = {
            prop: _parse_relaxation(prop_raw, idx, prop)
            for prop, prop_raw in properties.items()
            if prop in {"T1", "T2", "T2s"}
        }

    return TissueChannel(
        name=str(raw["name"]),
        label=int(raw["label"]),
        download_alias=str(raw["download_alias"]),
        proton_density=float(raw["proton_density"]),
        adc=float(raw["ADC"]),
        chi=float(raw["chi"]),
        fields=fields,
        provisional=bool(raw.get("provisional", False)),
    )


def _parse_relaxation(
    raw: dict[str, Any], channel_idx: int, prop: str
) -> RelaxationProperty:
    if not isinstance(raw, dict) or "mean_ms" not in raw:
        raise ValueError(f"Channel {channel_idx} property {prop} needs mean_ms")
    return RelaxationProperty(
        mean_ms=float(raw["mean_ms"]),
        std_ms=float(raw.get("std_ms", 0.0)),
        provisional=bool(raw.get("provisional", False)),
    )
