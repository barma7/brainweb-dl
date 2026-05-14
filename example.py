from pathlib import Path
from os.path import join as pjoin

from brainweb_dl import get_mri, get_quantitative_map, save_quantitative_map
from brainweb_dl import (
    ContrastMaps,
    ContrastSequence,
    NoiseConfig,
    get_quantitative_map,
    save_quantitative_map,
    save_synthesized_contrast,
    synthesize_contrast,)

out_dir = Path("brainweb-output")
out_dir.mkdir(exist_ok=True)

# 1. Download/load BrainWeb20 fuzzy segmentation
fuzzy, affine = get_mri(
    sub_id=4,
    contrast="fuzzy",
    brainweb_dir=out_dir / "cache",
    with_affine=True,
    force=False,  # force redownload for demonstration purposes
)

# chi = get_quantitative_map(fuzzy, "chi", affine=affine)
# save_quantitative_map(chi, out_dir / "brainweb_s04_chi.nii.gz")

# # 2. Generate an apparent T2 quantitative map
# t2 = get_quantitative_map(
#     fuzzy,
#     "T2",
#     affine=affine,
#     field_strength=3.0,
# )

# print(t2.property, t2.data.shape, t2.units)
# print(t2.metadata)

# # 3. Save as NIfTI + JSON sidecar
# save_quantitative_map(t2, out_dir / "brainweb_s04_T2.nii.gz")

# # 4. Generate total proton density too
# pd_total = get_quantitative_map(fuzzy, "PD_TOTAL", affine=affine)
# save_quantitative_map(pd_total, out_dir / "brainweb_s04_PD_TOTAL.nii.gz")

# t1 = get_quantitative_map(fuzzy, "T1", affine=affine, field_strength=3.0)
# save_quantitative_map(t1, out_dir / "brainweb_s04_T1.nii.gz")
t2s = get_quantitative_map(fuzzy, "T2s", affine=affine, field_strength=3.0)
save_quantitative_map(t2s, out_dir / "brainweb_s04_T2s.nii.gz")

pd_path = pjoin(out_dir, "brainweb_s04_PD_TOTAL.nii.gz")
t1_path = pjoin(out_dir, "brainweb_s04_T1.nii.gz")
t2s_path = pjoin(out_dir, "brainweb_s04_T2s.nii.gz")
t2_path = pjoin(out_dir, "brainweb_s04_T2.nii.gz")

t1w_noisy = synthesize_contrast(
    ContrastMaps(PD=pd_path, T1=t1_path, T2s=t2s_path),
    ContrastSequence(model="flash", TR=10e-3, TE=4e-3, flip_angle=20),
    contrast="T1w",
    noise=NoiseConfig(
        snr=10,
        fuzzy=out_dir / "cache" / "brainweb_s04_fuzzy.nii.gz",
        fraction_threshold=0.95,
        rng=123,
        ),
)

save_synthesized_contrast(t1w_noisy, out_dir / "t1w_flash_snr10.nii.gz")