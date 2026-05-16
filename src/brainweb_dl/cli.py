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
from .synthesize_contrast import (
    ContrastMaps,
    ContrastSequence,
    NoiseConfig,
    save_synthesized_contrast,
    synthesize_contrast,
)
from .nasal_air import (
    DEFAULT_T1W_SNR,
    DEFAULT_T1W_SEQUENCE,
    correct_fuzzy_nasal_air,
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


def parse_synth_args() -> argparse.Namespace:
    """Parse analytical contrast synthesis command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Synthesize analytical MRI contrasts from quantitative maps",
        epilog="For more information, visit https://github.com/paquiteau/brainweb-dl",
    )
    parser.add_argument(
        "--contrast",
        choices=["T1w", "T2w", "T2*w", "T2sw"],
        help="Requested contrast. Defaults from the sequence model.",
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=["spin-echo", "se", "spgr", "flash", "gre", "gradient-echo"],
        help="Analytical model to use.",
    )
    parser.add_argument("--pd", type=Path, required=True, help="PD map path")
    parser.add_argument("--t1", type=Path, help="T1 map path in seconds")
    parser.add_argument("--t2", type=Path, help="T2 map path in seconds")
    parser.add_argument("--t2s", type=Path, help="T2* map path in seconds")
    parser.add_argument("--tr", type=float, help="TR in seconds")
    parser.add_argument("--te", type=float, default=0.0, help="TE in seconds")
    parser.add_argument("--flip-angle", type=float, help="Flip angle in degrees")
    parser.add_argument("--snr", type=float, help="Requested white-matter SNR")
    parser.add_argument(
        "--fuzzy",
        type=Path,
        help="BrainWeb fuzzy segmentation path for white-matter SNR calibration",
    )
    parser.add_argument(
        "--wm-threshold",
        type=float,
        default=0.95,
        help="White-matter fuzzy fraction threshold for SNR calibration",
    )
    parser.add_argument("--rng", type=int, help="Random seed", default=None)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output .nii or .nii.gz path",
    )
    ns = parser.parse_args()
    if ns.snr is not None and ns.fuzzy is None:
        raise ValueError("--fuzzy is required when --snr is provided")
    return ns


def synth_main() -> None:
    """CLI interface for analytical contrast synthesis."""
    ns = parse_synth_args()
    maps = ContrastMaps(PD=ns.pd, T1=ns.t1, T2=ns.t2, T2s=ns.t2s)
    sequence = ContrastSequence(
        model=ns.model,
        TR=ns.tr,
        TE=ns.te,
        flip_angle=ns.flip_angle,
    )
    noise = None
    if ns.snr is not None:
        noise = NoiseConfig(
            snr=ns.snr,
            fuzzy=ns.fuzzy,
            fraction_threshold=ns.wm_threshold,
            rng=ns.rng,
        )
    result = synthesize_contrast(
        maps,
        sequence,
        contrast=ns.contrast.replace("sw", "*w") if ns.contrast else None,
        noise=noise,
    )
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    saved = save_synthesized_contrast(result, ns.output)
    print(f"Synthesized contrast saved to {saved}")


def parse_nasal_air_args() -> argparse.Namespace:
    """Parse nasal-air correction command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Correct BrainWeb20 fuzzy nasal air cavities with PARASIDE",
        epilog="For more information, visit https://github.com/paquiteau/brainweb-dl",
    )
    parser.add_argument("subject", type=int, choices=SUB_ID, help="BrainWeb20 subject ID")
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
        help="Corrected fuzzy .nii or .nii.gz output path",
    )
    parser.add_argument(
        "--paraside-env",
        type=Path,
        help="Conda environment path containing the PARASIDE CLI",
    )
    parser.add_argument(
        "--paraside-executable",
        type=Path,
        help="Direct PARASIDE executable path; mutually exclusive with --paraside-env",
    )
    parser.add_argument(
        "--paraside-model",
        type=Path,
        required=True,
        help="PARASIDE model weights path or model version",
    )
    parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Keep the synthesized T1w image used as PARASIDE input",
    )
    parser.add_argument("--force", action="store_true", help="Force fuzzy redownload")
    parser.add_argument(
        "--tr",
        type=float,
        default=DEFAULT_T1W_SEQUENCE.TR,
        help="SPGR/FLASH TR in seconds for synthesized T1w input",
    )
    parser.add_argument(
        "--te",
        type=float,
        default=DEFAULT_T1W_SEQUENCE.TE,
        help="SPGR/FLASH TE in seconds for synthesized T1w input",
    )
    parser.add_argument(
        "--flip-angle",
        type=float,
        default=DEFAULT_T1W_SEQUENCE.flip_angle,
        help="SPGR/FLASH flip angle in degrees for synthesized T1w input",
    )
    parser.add_argument(
        "--t1w-snr",
        type=float,
        default=DEFAULT_T1W_SNR,
        help=(
            "White-matter SNR for Rician noise in synthesized T1w input. "
            "Use 0 to disable noise."
        ),
    )
    parser.add_argument(
        "--t1w-rng",
        type=int,
        help="Random seed for synthesized T1w noise",
        default=None,
    )
    ns = parser.parse_args()
    if ns.paraside_env is None and ns.paraside_executable is None:
        raise ValueError("--paraside-env or --paraside-executable is required")
    if ns.paraside_env is not None and ns.paraside_executable is not None:
        raise ValueError("Use either --paraside-env or --paraside-executable, not both")
    return ns


def nasal_air_main() -> None:
    """CLI interface for BrainWeb20 nasal-air fuzzy correction."""
    ns = parse_nasal_air_args()
    sequence = ContrastSequence(
        model="flash",
        TR=ns.tr,
        TE=ns.te,
        flip_angle=ns.flip_angle,
    )
    result = correct_fuzzy_nasal_air(
        ns.subject,
        brainweb_dir=get_brainweb_dir(ns.brainweb_dir),
        output=ns.output,
        paraside_env=ns.paraside_env,
        paraside_executable=ns.paraside_executable,
        paraside_model=ns.paraside_model,
        sequence=sequence,
        t1w_snr=None if ns.t1w_snr == 0 else ns.t1w_snr,
        t1w_rng=ns.t1w_rng,
        keep_intermediates=ns.keep_intermediates,
        force=ns.force,
    )
    print(f"Corrected fuzzy segmentation saved to {result.corrected_path}")
