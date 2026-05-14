from pathlib import Path

from brainweb_dl import get_mri, get_quantitative_map, save_quantitative_map

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

chi = get_quantitative_map(fuzzy, "chi", affine=affine)
save_quantitative_map(chi, out_dir / "brainweb_s04_chi.nii.gz")

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
