from brainweb_dl import correct_fuzzy_nasal_air

result = correct_fuzzy_nasal_air(
    subject=4,
    brainweb_dir=r"C:\Users\marco\Research\Projects\barma7_repositories\brainweb-dl\brainweb-output\cache",
    output=r"C:\Users\marco\Research\Projects\barma7_repositories\brainweb-dl\brainweb-output\brainweb_s04_fuzzy.nasal-air-corrected.nii.gz",
    paraside_env=r"C:\Users\marco\.conda\envs\paraside",
    paraside_model=r"C:\Users\marco\Nextcloud\third_parties_packages\paraside\Paraside_model_weights_v1",
    keep_intermediates=True,
)

print(result.corrected_path)
print(result.sidecar_path)
print(result.paraside_mask_path)
print(result.patched_voxels)

from brainweb_dl import get_quantitative_map, save_quantitative_map

chi = get_quantitative_map(
    result.corrected_path,
    "chi",
    field_strength=3.0,
)

save_quantitative_map(
    chi,
    r"C:\Users\marco\Research\Projects\barma7_repositories\brainweb-dl\brainweb-output\brainweb_s04_chi_corrected.nii.gz",
)