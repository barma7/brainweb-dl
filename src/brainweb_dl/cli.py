"""CLI function for the package."""

from __future__ import annotations
import argparse
from pathlib import Path
from tqdm import tqdm

from ._brainweb import (
    SUB_ID,
    Segmentation,
    get_brainweb1_seg,
    get_brainweb20,
    get_brainweb_dir,
    load_array,
    save_array,
)
from .mri import get_mri
from .qmap import (
    SUPPORTED_PROPERTIES,
    get_quantitative_map,
    save_quantitative_map,
    save_quantitative_maps,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Get data from the brainWeb Dataset",
        epilog="For more information, visit https://github.com/paquiteau/brainweb-dl",
    )
    parser.add_argument(
        "subject",
        type=int,
        help="Subject ID",
        nargs="*",
        choices=[-1, 0, *SUB_ID],
        default=-1,
    )
    parser.add_argument(
        "--contrast",
        type=str,
        help="Contrast to download/create. ",
        choices=["T1", "T2", "T2*", "crisp", "fuzzy"],
    )
    parser.add_argument(
        "--brainweb-dir",
        type=Path,
        help=(
            "BrainWeb cache/download directory, overrides the environment variable "
            "BRAINWEB_DIR"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for final CLI output files. Default: current working directory",
    )
    parser.add_argument(
        "--extension",
        type=str,
        help="Output format. Default: nii.gz",
        nargs="?",
        choices=["nii.gz", "nii", "npy"],
        default="nii.gz",
    )
    parser.add_argument("--rng", type=int, help="Random seed", default=None)
    parser.add_argument("--all", action="store_true", help="Download all subjects")

    ns = parser.parse_args()
    if ns.all and ns.subject == -1:
        ns.subject = [*SUB_ID]
    elif ns.subject == -1:
        raise ValueError("Subject ID or --all is required")
    return ns


def _as_subject_list(subject: int | list[int]) -> list[int]:
    """Normalize parsed subject input to a list."""
    if isinstance(subject, int):
        return [subject]
    return subject


def _output_path(output_dir: Path, subject: int, contrast: str, extension: str) -> Path:
    """Build the final CLI output path."""
    return output_dir / f"brainweb_{subject}_{contrast}.{extension}"


def main() -> None:
    """CLI interface."""
    ns = parse_args()
    brainweb_dir = get_brainweb_dir(ns.brainweb_dir)
    output_dir = ns.output_dir if ns.output_dir is not None else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames: list[Path] = []
    subjects = _as_subject_list(ns.subject)

    if ns.contrast in ["T1", "T2", "T2*"]:
        for sid in tqdm(subjects):
            array, affine = get_mri(
                sid, ns.contrast, brainweb_dir=brainweb_dir, with_affine=True
            )
            filename = _output_path(output_dir, sid, ns.contrast, ns.extension)
            save_array(array, affine, filename)
            filenames.append(filename)
    elif ns.contrast in ["crisp", "fuzzy"]:
        for sid in tqdm(subjects):
            if sid == 0:
                cache_path = get_brainweb1_seg(ns.contrast, brainweb_dir=brainweb_dir)
            else:
                cache_path = get_brainweb20(
                    sid, segmentation=ns.contrast, brainweb_dir=brainweb_dir
                )
            data, affine = load_array(cache_path)
            filename = _output_path(output_dir, sid, ns.contrast, ns.extension)
            save_array(data, affine, filename)
            filenames.append(filename)
    else:
        raise ValueError(f"Unknown contrast {ns.contrast}")

    if len(filenames) == 1:
        print(f"Data saved to {filenames[0]}")
    else:
        print(f"{len(filenames)} files saved to {output_dir}")


if __name__ == "__main__":
    main()


def parse_qmap_args() -> argparse.Namespace:
    """Parse quantitative-map command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate BrainWeb20 quantitative maps from fuzzy segmentations",
        epilog="For more information, visit https://github.com/paquiteau/brainweb-dl",
    )
    parser.add_argument("subject", type=int, choices=SUB_ID, help="BrainWeb20 subject ID")
    parser.add_argument(
        "--property",
        required=True,
        help="Quantitative property to generate, or 'all'",
        choices=[*sorted(SUPPORTED_PROPERTIES), "T2*", "all"],
    )
    parser.add_argument(
        "--field-strength",
        type=float,
        default=3.0,
        help="Field strength in tesla. Default: 3.0",
    )
    parser.add_argument(
        "--brainweb-dir",
        type=Path,
        help=(
            "BrainWeb cache/download directory, overrides the environment variable "
            "BRAINWEB_DIR"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output .h5/.hdf5/.nii/.nii.gz path, or a directory for --property all",
    )
    parser.add_argument("--force", action="store_true", help="Force fuzzy redownload")
    parser.add_argument(
        "--stochastic",
        action="store_true",
        help="Sample relaxation values from JSON mean/std values",
    )
    parser.add_argument("--rng", type=int, help="Random seed", default=None)
    return parser.parse_args()


def qmap_main() -> None:
    """CLI interface for quantitative BrainWeb20 maps."""
    ns = parse_qmap_args()
    brainweb_dir = get_brainweb_dir(ns.brainweb_dir)
    fuzzy_path = get_brainweb20(
        ns.subject,
        segmentation=Segmentation.FUZZY,
        brainweb_dir=brainweb_dir,
        force=ns.force,
    )
    properties = (
        sorted(SUPPORTED_PROPERTIES)
        if ns.property == "all"
        else [ns.property.replace("*", "s")]
    )
    results = [
        get_quantitative_map(
            fuzzy_path,
            prop,
            field_strength=ns.field_strength,
            stochastic=ns.stochastic,
            rng=ns.rng,
        )
        for prop in properties
    ]

    output = ns.output
    if len(results) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        saved = save_quantitative_map(results[0], output)
        print(f"Quantitative map saved to {saved}")
        return

    if output.suffix.lower() in {".h5", ".hdf5"}:
        output.parent.mkdir(parents=True, exist_ok=True)
        saved = save_quantitative_maps(results, output)
        print(f"{len(results)} quantitative maps saved to {saved}")
        return

    output.mkdir(parents=True, exist_ok=True)
    for result in results:
        save_quantitative_map(result, output / f"brainweb_{ns.subject}_{result.property}.nii.gz")
    print(f"{len(results)} quantitative maps saved to {output}")
