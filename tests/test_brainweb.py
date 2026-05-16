"""Test for the brainweb module."""

import json
from pathlib import Path
import numpy as np
from nibabel import nifti1 as nifti
import subprocess

import pytest
from brainweb_dl import (
    ContrastMaps,
    ContrastSequence,
    NoiseConfig,
    get_mri,
    get_brainweb20_multiple,
    get_brainweb1_seg,
    get_quantitative_map,
    load_tissue_properties,
    save_synthesized_contrast,
    save_quantitative_map,
    synthesize_contrast,
    patch_fuzzy_with_air_mask,
)
import brainweb_dl.cli as cli
import brainweb_dl.mri as mri
import brainweb_dl.nasal_air as nasal_air
import brainweb_dl._brainweb as brainweb
from brainweb_dl._brainweb import (
    _centered_affine,
    _request_get_brainweb_affine,
    load_array,
    save_array,
)


def test_centered_affine_from_shape_and_resolution():
    """Test centered affine generation from spatial shape and resolution."""
    affine = _centered_affine((362, 434, 362), (0.5, 0.5, 0.5))

    expected = np.array(
        [
            [0.5, 0.0, 0.0, -90.5],
            [0.0, 0.5, 0.0, -108.5],
            [0.0, 0.0, 0.5, -90.5],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    np.testing.assert_array_equal(affine, expected)


@pytest.mark.parametrize(
    "download_cmd, expected",
    [
        (
            "T1+ICBM+normal+1mm+pn0+rf0",
            np.array(
                [
                    [1.0, 0.0, 0.0, -90.5],
                    [0.0, 1.0, 0.0, -108.5],
                    [0.0, 0.0, 1.0, -90.5],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=np.float32,
            ),
        ),
        (
            "phantom_1.0mm_normal_fuzzy",
            np.array(
                [
                    [1.0, 0.0, 0.0, -90.5],
                    [0.0, 1.0, 0.0, -108.5],
                    [0.0, 0.0, 1.0, -90.5],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=np.float32,
            ),
        ),
        (
            "subject04_t1w",
            np.array(
                [
                    [1.0, 0.0, 0.0, -90.5],
                    [0.0, 1.0, 0.0, -128.0],
                    [0.0, 0.0, 1.0, -128.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=np.float32,
            ),
        ),
        (
            "subject04_fuzzy",
            np.array(
                [
                    [0.5, 0.0, 0.0, -90.5],
                    [0.0, 0.5, 0.0, -108.5],
                    [0.0, 0.0, 0.5, -90.5],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=np.float32,
            ),
        ),
    ],
)
def test_request_get_brainweb_affine(download_cmd, expected):
    """Test affine selection for native BrainWeb products."""
    np.testing.assert_array_equal(_request_get_brainweb_affine(download_cmd), expected)


def test_save_and_load_array_preserves_nifti_affine(tmp_path):
    """Test that NIfTI save/load preserves affine metadata."""
    path = tmp_path / "array.nii.gz"
    data = np.arange(8, dtype=np.uint16).reshape((2, 2, 2))
    affine = _centered_affine((2, 2, 2), 2.0)

    save_array(data, affine, path)
    loaded_data, loaded_affine = load_array(path)

    np.testing.assert_array_equal(loaded_data, data)
    np.testing.assert_array_equal(loaded_affine, affine)


def test_generated_v2_contrast_returns_segmentation_affine(monkeypatch, tmp_path):
    """Test generated v2 contrasts are no longer provided by get_mri."""
    path = tmp_path / "brainweb_s04_fuzzy.nii.gz"
    affine = _request_get_brainweb_affine("subject04_fuzzy")
    nifti.save(nifti.Nifti1Image(np.zeros((2, 2, 2, 1), dtype=np.uint16), affine), path)

    seen = {}

    def fake_get_brainweb20(*args, **kwargs):
        seen.update(kwargs)
        return path

    monkeypatch.setattr(mri, "get_brainweb20", fake_get_brainweb20)
    brainweb_dir = tmp_path / "cache"
    with pytest.raises(ValueError, match="get_quantitative_map"):
        get_mri(4, "T2*", brainweb_dir=brainweb_dir, with_affine=True)

    assert seen == {}


@pytest.mark.parametrize("contrast", ["crisp", "fuzzy"])
def test_get_mri20_segmentation_passes_brainweb_dir(monkeypatch, tmp_path, contrast):
    """Test v2 segmentations honor the caller-provided BrainWeb directory."""
    path = tmp_path / f"brainweb_s04_{contrast}.nii.gz"
    affine = _request_get_brainweb_affine(f"subject04_{contrast}")
    shape = (2, 2, 2, 1) if contrast == "fuzzy" else (2, 2, 2)
    nifti.save(nifti.Nifti1Image(np.zeros(shape, dtype=np.uint16), affine), path)
    seen = {}

    def fake_get_brainweb20(*args, **kwargs):
        seen.update(kwargs)
        return path

    monkeypatch.setattr(mri, "get_brainweb20", fake_get_brainweb20)

    brainweb_dir = tmp_path / "cache"
    get_mri(4, contrast, brainweb_dir=brainweb_dir)

    assert seen["brainweb_dir"] == brainweb_dir


def test_cli_contrast_writes_to_output_dir(monkeypatch, tmp_path, capsys):
    """Test CLI contrast output is written under --output-dir."""
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "out"
    seen = {}

    def fake_get_mri(*args, **kwargs):
        seen.update(kwargs)
        return np.zeros((2, 2, 2), dtype=np.float32), np.eye(4, dtype=np.float32)

    monkeypatch.setattr(cli, "get_mri", fake_get_mri)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl",
            "4",
            "--contrast",
            "T1",
            "--brainweb-dir",
            str(cache_dir),
            "--output-dir",
            str(output_dir),
            "--extension",
            "nii.gz",
        ],
    )

    cli.main()

    output_path = output_dir / "brainweb_4_T1.nii.gz"
    assert output_path.exists()
    assert not (tmp_path / "brainweb_4_T1.nii.gz").exists()
    assert seen["brainweb_dir"] == cache_dir
    assert str(output_path) in capsys.readouterr().out


def test_cli_segmentation_writes_to_output_dir(monkeypatch, tmp_path, capsys):
    """Test CLI segmentation output is written under --output-dir."""
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "out"
    cache_path = cache_dir / "brainweb_s04_fuzzy.nii.gz"
    affine = _request_get_brainweb_affine("subject04_fuzzy")
    seen = {}

    def fake_get_brainweb20(*args, **kwargs):
        seen.update(kwargs)
        cache_dir.mkdir(parents=True, exist_ok=True)
        save_array(np.zeros((2, 2, 2, 1), dtype=np.uint16), affine, cache_path)
        return cache_path

    monkeypatch.setattr(cli, "get_brainweb20", fake_get_brainweb20)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl",
            "4",
            "--contrast",
            "fuzzy",
            "--brainweb-dir",
            str(cache_dir),
            "--output-dir",
            str(output_dir),
            "--extension",
            "nii.gz",
        ],
    )

    cli.main()

    output_path = output_dir / "brainweb_4_fuzzy.nii.gz"
    assert cache_path.exists()
    assert output_path.exists()
    assert not (tmp_path / "brainweb_4_fuzzy.nii.gz").exists()
    assert seen["brainweb_dir"] == cache_dir
    captured = capsys.readouterr().out
    assert str(output_path) in captured
    assert str(cache_path) not in captured


@pytest.mark.parametrize(
    "sub_id, contrast, res, noise, field_value",
    [
        (0, "T1", 1, 1, 20),
        (0, "T2", 3, 5, 40),
        (0, "PD", 7, 9, 0),
    ],
)
def test_get_mri1(sub_id, contrast, res, noise, field_value, bw_dir):
    """Test retrieval of available data."""
    data = get_mri(
        sub_id,
        contrast,
        brainweb_dir=bw_dir,
        download_res=res,
        noise=noise,
        field_value=field_value,
    )

    assert data.shape == (int(np.rint(181 / res)), 217, 181)


@pytest.mark.parametrize(
    "kwargs", [{"download_res": None}, {"noise": None}, {"field_value": None}]
)
def test_get_mri1_unavailable(kwargs, bw_dir):
    """Test retrieval of unavailable data."""
    with pytest.raises(ValueError):
        get_mri(0, "T1", **kwargs, brainweb_dir=bw_dir)


def test_get_mri20T1(bw_dir, force):
    """Test retrieval of available data."""
    data = get_mri(4, "T1", brainweb_dir=bw_dir, force=force)
    assert data.shape == (181, 256, 256)


@pytest.mark.parametrize("contrast", ["T2*"])
def test_get_mri20_custom(contrast, bw_dir, force):
    """Test BrainWeb20 generated maps moved out of get_mri."""
    with pytest.raises(ValueError, match="get_quantitative_map"):
        get_mri(4, contrast, brainweb_dir=bw_dir, force=force)


@pytest.mark.parametrize("contrast", ["T2*"])
def test_get_mri1_custom(contrast, bw_dir, force):
    """Test legacy BrainWeb1 CSV synthesis is not supported."""
    with pytest.raises(ValueError, match="no longer supported"):
        get_mri(0, contrast, brainweb_dir=bw_dir, force=force)


def test_load_brainweb20_tissue_properties():
    """Test structured BrainWeb20 tissue-property metadata loads."""
    table = load_tissue_properties()

    assert table.dataset == "BrainWeb20"
    assert len(table.channels) == 12
    assert table.units["T2"] == "ms"
    assert table.channels[0].name == "background"
    assert table.channels[0].chi == pytest.approx(0.36)


def test_quantitative_map_volume_fraction_without_renormalization():
    """Test fuzzy channels are divided by 4095 without renormalization."""
    fuzzy = np.zeros((1, 1, 1, 2), dtype=np.uint16)
    fuzzy[..., 0] = 2048
    fuzzy[..., 1] = 1024

    vf = get_quantitative_map(fuzzy, "VF")
    total = get_quantitative_map(fuzzy, "VF_TOTAL")

    np.testing.assert_allclose(vf.data[0, 0, 0, :], [2048 / 4095, 1024 / 4095])
    np.testing.assert_allclose(total.data[0, 0, 0], (2048 + 1024) / 4095)


def test_quantitative_map_apparent_t1_uses_pd_weighted_rates():
    """Test apparent T1 uses proton-density-weighted rate mixing."""
    fuzzy = np.zeros((1, 1, 1, 4), dtype=np.float32)
    fuzzy[..., 2] = 0.5
    fuzzy[..., 3] = 0.5

    result = get_quantitative_map(fuzzy, "T1")
    w_gm = 0.5 * 0.86
    w_wm = 0.5 * 0.77
    expected = 1.0 / ((w_gm / 1.05 + w_wm / 0.7) / (w_gm + w_wm))

    assert result.units == "s"
    np.testing.assert_allclose(result.data[0, 0, 0], expected, rtol=1e-6)


def test_quantitative_map_pd_adc_and_chi_models():
    """Test PD, ADC, and chi weighted models."""
    fuzzy = np.zeros((1, 1, 1, 5), dtype=np.float32)
    fuzzy[..., 0] = 0.5
    fuzzy[..., 4] = 0.5

    pd_total = get_quantitative_map(fuzzy, "PD_TOTAL")
    adc = get_quantitative_map(fuzzy, "ADC", field_strength=7.0)
    chi = get_quantitative_map(fuzzy, "chi", field_strength=7.0)

    np.testing.assert_allclose(pd_total.data[0, 0, 0], 0.5)
    np.testing.assert_allclose(adc.data[0, 0, 0], 0.00005)
    np.testing.assert_allclose(chi.data[0, 0, 0], 0.5 * 0.36 + 0.5 * 0.6)


def test_quantitative_map_stochastic_is_reproducible():
    """Test stochastic relaxation sampling uses the RNG seed."""
    fuzzy = np.zeros((2, 1, 1, 3), dtype=np.float32)
    fuzzy[..., 2] = 1.0

    first = get_quantitative_map(fuzzy, "T2", stochastic=True, rng=123)
    second = get_quantitative_map(fuzzy, "T2", stochastic=True, rng=123)

    np.testing.assert_array_equal(first.data, second.data)


def test_save_quantitative_map_writes_nifti_and_sidecar(tmp_path):
    """Test NIfTI quantitative-map output includes JSON metadata sidecar."""
    fuzzy = np.zeros((1, 1, 1, 3), dtype=np.float32)
    fuzzy[..., 2] = 1.0
    result = get_quantitative_map(fuzzy, "T2")
    path = tmp_path / "t2.nii.gz"

    save_quantitative_map(result, path)

    assert path.exists()
    sidecar = tmp_path / "t2.json"
    assert sidecar.exists()
    assert '"property": "T2"' in sidecar.read_text()


def test_qmap_cli_generates_nifti(monkeypatch, tmp_path, capsys):
    """Test quantitative-map CLI downloads fuzzy data and saves NIfTI output."""
    fuzzy_path = tmp_path / "brainweb_s04_fuzzy.nii.gz"
    fuzzy = np.zeros((1, 1, 1, 3), dtype=np.uint16)
    fuzzy[..., 2] = 4095
    save_array(fuzzy, np.eye(4, dtype=np.float32), fuzzy_path)

    monkeypatch.setattr(cli, "get_brainweb20", lambda *args, **kwargs: fuzzy_path)
    output = tmp_path / "t2.nii.gz"
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-qmap",
            "4",
            "--property",
            "T2",
            "--output",
            str(output),
        ],
    )

    cli.qmap_main()

    assert output.exists()
    assert (tmp_path / "t2.json").exists()
    assert str(output) in capsys.readouterr().out


def test_qmap_cli_generates_all_hdf5(monkeypatch, tmp_path, capsys):
    """Test quantitative-map CLI can save all supported maps in one HDF5 file."""
    fuzzy_path = tmp_path / "brainweb_s04_fuzzy.nii.gz"
    fuzzy = np.zeros((1, 1, 1, 3), dtype=np.uint16)
    fuzzy[..., 2] = 4095
    save_array(fuzzy, np.eye(4, dtype=np.float32), fuzzy_path)

    monkeypatch.setattr(cli, "get_brainweb20", lambda *args, **kwargs: fuzzy_path)
    output = tmp_path / "qmaps.h5"
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-qmap",
            "4",
            "--property",
            "all",
            "--output",
            str(output),
        ],
    )

    cli.qmap_main()

    assert output.exists()
    assert str(output) in capsys.readouterr().out


def test_synthesize_spgr_uses_only_required_maps():
    """Test SPGR T1w synthesis with TE=0 does not require T2/T2s."""
    pd = np.full((1, 1, 1), 0.8, dtype=np.float32)
    t1 = np.full((1, 1, 1), 1.2, dtype=np.float32)

    result = synthesize_contrast(
        ContrastMaps(PD=pd, T1=t1),
        ContrastSequence(model="flash", TR=0.03, TE=0.0, flip_angle=20),
    )

    alpha = np.deg2rad(20)
    e1 = np.exp(-0.03 / 1.2)
    expected = 0.8 * np.sin(alpha) * (1 - e1) / (1 - np.cos(alpha) * e1)
    np.testing.assert_allclose(result.data[0, 0, 0], expected, rtol=1e-6)
    assert result.required_maps == ["PD", "T1"]


def test_synthesize_signal_models():
    """Test spin-echo, SPGR echo decay, and GRE T2* formulas."""
    pd = np.full((1, 1, 1), 0.75, dtype=np.float32)
    t1 = np.full((1, 1, 1), 1.0, dtype=np.float32)
    t2 = np.full((1, 1, 1), 0.08, dtype=np.float32)
    t2s = np.full((1, 1, 1), 0.04, dtype=np.float32)

    spin = synthesize_contrast(
        ContrastMaps(PD=pd, T1=t1, T2=t2),
        ContrastSequence(model="spin-echo", TR=2.0, TE=0.08),
        contrast="T2w",
    )
    spgr = synthesize_contrast(
        ContrastMaps(PD=pd, T1=t1, T2s=t2s),
        ContrastSequence(model="spgr", TR=0.025, TE=0.004, flip_angle=15),
    )
    gre = synthesize_contrast(
        ContrastMaps(PD=pd, T2s=t2s),
        ContrastSequence(model="gre", TE=0.02),
    )

    np.testing.assert_allclose(
        spin.data[0, 0, 0],
        0.75 * (1 - np.exp(-2.0 / 1.0)) * np.exp(-0.08 / 0.08),
        rtol=1e-6,
    )
    alpha = np.deg2rad(15)
    e1 = np.exp(-0.025 / 1.0)
    np.testing.assert_allclose(
        spgr.data[0, 0, 0],
        0.75
        * np.sin(alpha)
        * (1 - e1)
        / (1 - np.cos(alpha) * e1)
        * np.exp(-0.004 / 0.04),
        rtol=1e-6,
    )
    np.testing.assert_allclose(
        gre.data[0, 0, 0], 0.75 * np.exp(-0.02 / 0.04), rtol=1e-6
    )


def test_synthesize_path_loading_and_affine_validation(tmp_path):
    """Test path inputs load arrays, preserve affine, and reject mismatches."""
    pd_path = tmp_path / "pd.nii.gz"
    t1_path = tmp_path / "t1.nii.gz"
    t2s_path = tmp_path / "t2s.nii.gz"
    affine = np.diag([2.0, 2.0, 2.0, 1.0]).astype(np.float32)

    save_array(np.ones((2, 2, 2), dtype=np.float32), affine, pd_path)
    save_array(np.ones((2, 2, 2), dtype=np.float32), affine, t1_path)
    save_array(np.ones((2, 2, 2), dtype=np.float32), affine, t2s_path)

    result = synthesize_contrast(
        ContrastMaps(PD=pd_path, T1=t1_path, T2s=t2s_path),
        ContrastSequence(model="spgr", TR=0.025, TE=0.004, flip_angle=20),
    )

    np.testing.assert_array_equal(result.affine, affine)

    bad_affine_path = tmp_path / "t2s_bad.nii.gz"
    save_array(np.ones((2, 2, 2), dtype=np.float32), np.eye(4), bad_affine_path)
    with pytest.raises(ValueError, match="affine"):
        synthesize_contrast(
            ContrastMaps(PD=pd_path, T1=t1_path, T2s=bad_affine_path),
            ContrastSequence(model="spgr", TR=0.025, TE=0.004, flip_angle=20),
        )


def test_synthesize_rician_noise_uses_white_matter_mask():
    """Test Rician noise calibration uses the BrainWeb white-matter channel."""
    pd = np.ones((2, 1, 1), dtype=np.float32)
    t2s = np.ones((2, 1, 1), dtype=np.float32)
    fuzzy = np.zeros((2, 1, 1, 4), dtype=np.float32)
    fuzzy[..., 3] = 1.0

    kwargs = dict(
        maps=ContrastMaps(PD=pd, T2s=t2s),
        sequence=ContrastSequence(model="gre", TE=0.0),
        noise=NoiseConfig(snr=20, fuzzy=fuzzy, rng=123),
    )
    first = synthesize_contrast(**kwargs)
    second = synthesize_contrast(**kwargs)

    np.testing.assert_array_equal(first.data, second.data)
    assert first.metadata["noise"]["sigma"] == pytest.approx(0.05)

    fuzzy[..., 3] = 0.0
    with pytest.raises(ValueError, match="mask is empty"):
        synthesize_contrast(
            ContrastMaps(PD=pd, T2s=t2s),
            ContrastSequence(model="gre", TE=0.0),
            noise=NoiseConfig(snr=20, fuzzy=fuzzy),
        )


def test_save_synthesized_contrast_writes_sidecar(tmp_path):
    """Test synthesized contrast persistence writes image and metadata."""
    result = synthesize_contrast(
        ContrastMaps(PD=np.ones((1, 1, 1)), T2s=np.ones((1, 1, 1))),
        ContrastSequence(model="gre", TE=0.0),
    )
    path = tmp_path / "synth.nii.gz"

    save_synthesized_contrast(result, path)

    assert path.exists()
    metadata = json.loads((tmp_path / "synth.json").read_text())
    assert metadata["contrast"] == "T2*w"
    assert metadata["required_maps"] == ["PD", "T2s"]


def test_synth_cli_generates_nifti(monkeypatch, tmp_path, capsys):
    """Test analytical synthesis CLI consumes map paths and saves output."""
    pd_path = tmp_path / "pd.nii.gz"
    t2s_path = tmp_path / "t2s.nii.gz"
    save_array(np.ones((1, 1, 1), dtype=np.float32), np.eye(4), pd_path)
    save_array(np.ones((1, 1, 1), dtype=np.float32), np.eye(4), t2s_path)
    output = tmp_path / "t2sw.nii.gz"

    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-synth",
            "--model",
            "gre",
            "--contrast",
            "T2*w",
            "--pd",
            str(pd_path),
            "--t2s",
            str(t2s_path),
            "--te",
            "0",
            "--output",
            str(output),
        ],
    )

    cli.synth_main()

    assert output.exists()
    assert (tmp_path / "t2sw.json").exists()
    assert str(output) in capsys.readouterr().out


def test_synth_cli_snr_requires_fuzzy(monkeypatch):
    """Test CLI refuses SNR calibration without a fuzzy segmentation path."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-synth",
            "--model",
            "gre",
            "--pd",
            "pd.nii.gz",
            "--t2s",
            "t2s.nii.gz",
            "--snr",
            "20",
            "--output",
            "out.nii.gz",
        ],
    )

    with pytest.raises(ValueError, match="--fuzzy"):
        cli.parse_synth_args()


def test_patch_fuzzy_with_air_mask_integer_nonzero_labels():
    """Test integer fuzzy patching converts every nonzero mask label."""
    fuzzy = np.zeros((2, 1, 1, 3), dtype=np.uint16)
    fuzzy[0, 0, 0] = [0, 100, 200]
    fuzzy[1, 0, 0] = [0, 300, 400]
    mask = np.array([[[1]], [[9]]], dtype=np.uint16)

    patched = patch_fuzzy_with_air_mask(fuzzy, mask)

    np.testing.assert_array_equal(patched[0, 0, 0], [4095, 0, 0])
    np.testing.assert_array_equal(patched[1, 0, 0], [4095, 0, 0])
    np.testing.assert_array_equal(fuzzy[0, 0, 0], [0, 100, 200])


def test_patch_fuzzy_with_air_mask_normalized_float():
    """Test normalized fuzzy patching uses 1.0 for background."""
    fuzzy = np.zeros((1, 1, 2, 2), dtype=np.float32)
    fuzzy[0, 0, 0] = [0.2, 0.8]
    fuzzy[0, 0, 1] = [0.3, 0.7]
    mask = np.array([[[107, 0]]], dtype=np.uint16)

    patched = patch_fuzzy_with_air_mask(fuzzy, mask)

    np.testing.assert_allclose(patched[0, 0, 0], [1.0, 0.0])
    np.testing.assert_allclose(patched[0, 0, 1], fuzzy[0, 0, 1])


def test_patch_fuzzy_geometry_validation():
    """Test shape and affine mismatch validation before patching."""
    fuzzy = np.zeros((1, 1, 1, 2), dtype=np.uint16)
    mask = np.zeros((2, 1, 1), dtype=np.uint16)

    with pytest.raises(ValueError, match="shape"):
        patch_fuzzy_with_air_mask(fuzzy, mask)

    with pytest.raises(ValueError, match="affine"):
        nasal_air._validate_fuzzy_mask_geometry(
            fuzzy,
            np.zeros((1, 1, 1), dtype=np.uint16),
            np.eye(4, dtype=np.float32),
            np.diag([2, 1, 1, 1]).astype(np.float32),
        )


def test_generate_t1w_for_paraside_preserves_fuzzy_grid(tmp_path):
    """Test synthesized PARASIDE input preserves grid and uses noisy TE default."""
    fuzzy = np.zeros((1, 1, 1, 4), dtype=np.uint16)
    fuzzy[..., 3] = 4095
    affine = np.diag([0.5, 0.5, 0.5, 1.0]).astype(np.float32)
    output = tmp_path / "t1w.nii.gz"

    saved = nasal_air.generate_t1w_for_paraside(fuzzy, output, affine=affine, rng=123)
    data, loaded_affine = load_array(saved)
    metadata = json.loads((tmp_path / "t1w.json").read_text())

    assert data.shape == (1, 1, 1)
    np.testing.assert_array_equal(loaded_affine, affine)
    assert metadata["sequence"]["TE"] == pytest.approx(4e-3)
    assert metadata["required_maps"] == ["PD", "T1", "T2s"]
    assert metadata["noise"]["requested_snr"] == pytest.approx(10.0)


def test_paraside_command_construction_modes(monkeypatch, tmp_path):
    """Test conda and direct executable PARASIDE command construction."""
    image = tmp_path / "input.nii.gz"
    model = tmp_path / "weights"
    env = tmp_path / "paraside-env"
    exe = tmp_path / "paraside.exe"
    conda = tmp_path / "conda.exe"
    monkeypatch.setenv("CONDA_EXE", str(conda))

    assert nasal_air.build_paraside_command(image, model, paraside_env=env) == [
        str(conda),
        "run",
        "--no-capture-output",
        "-p",
        str(env),
        "paraside",
        "--i",
        str(image),
        "--m",
        str(model),
    ]
    assert nasal_air.build_paraside_command(
        image, model, paraside_executable=exe
    ) == [str(exe), "--i", str(image), "--m", str(model)]


def test_run_paraside_failure_raises(monkeypatch):
    """Test subprocess failures are surfaced as runtime errors."""

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=2,
            cmd=args[0],
            output="out",
            stderr="err",
        )

    monkeypatch.setattr(nasal_air.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="exit code 2"):
        nasal_air.run_paraside(["paraside"])


def test_expected_paraside_output_path(tmp_path):
    """Test PARASIDE CLI output path convention."""
    image = tmp_path / "brainweb_s04_T1w.nii.gz"

    assert nasal_air.expected_paraside_output_path(image) == (
        tmp_path / "paraside_output" / "brainweb_s04_T1w_nose_segmentation.nii.gz"
    )


def test_correct_fuzzy_nasal_air_workflow(monkeypatch, tmp_path):
    """Test Python workflow orchestration with PARASIDE seams monkeypatched."""
    source = tmp_path / "cache" / "brainweb_s04_fuzzy.nii.gz"
    source.parent.mkdir()
    fuzzy = np.zeros((1, 1, 2, 3), dtype=np.uint16)
    fuzzy[..., 1] = 100
    affine = np.eye(4, dtype=np.float32)
    save_array(fuzzy, affine, source)
    output = tmp_path / "brainweb_s04_fuzzy.nasal-air-corrected.nii.gz"

    def fake_generate(fuzzy_path, output_path, **kwargs):
        save_array(np.zeros((1, 1, 2), dtype=np.float32), affine, output_path)
        return output_path

    def fake_run(command):
        input_path = Path(command[command.index("--i") + 1])
        mask_path = nasal_air.expected_paraside_output_path(input_path)
        mask_path.parent.mkdir()
        save_array(np.array([[[1, 0]]], dtype=np.uint16), affine, mask_path)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(nasal_air, "get_brainweb20", lambda *args, **kwargs: source)
    monkeypatch.setattr(nasal_air, "generate_t1w_for_paraside", fake_generate)
    monkeypatch.setattr(nasal_air, "run_paraside", fake_run)

    result = nasal_air.correct_fuzzy_nasal_air(
        4,
        output=output,
        paraside_env=tmp_path / "env",
        paraside_model=tmp_path / "weights",
        keep_intermediates=True,
    )
    corrected, _ = load_array(output)
    metadata = json.loads((tmp_path / "brainweb_s04_fuzzy.nasal-air-corrected.json").read_text())

    np.testing.assert_array_equal(corrected[0, 0, 0], [4095, 0, 0])
    np.testing.assert_array_equal(corrected[0, 0, 1], fuzzy[0, 0, 1])
    assert result.patched_voxels == 1
    assert metadata["patched_voxels"] == 1
    assert metadata["paraside_mask_rule"] == "mask != 0"
    assert metadata["source_fuzzy_path"] == str(source)


def test_correct_fuzzy_nasal_air_missing_paraside_output(monkeypatch, tmp_path):
    """Test workflow fails when PARASIDE does not create its expected mask."""
    source = tmp_path / "source.nii.gz"
    save_array(np.zeros((1, 1, 1, 2), dtype=np.uint16), np.eye(4), source)

    def fake_generate(fuzzy_path, output_path, **kwargs):
        save_array(np.zeros((1, 1, 1), dtype=np.float32), np.eye(4), output_path)
        return output_path

    monkeypatch.setattr(nasal_air, "get_brainweb20", lambda *args, **kwargs: source)
    monkeypatch.setattr(nasal_air, "generate_t1w_for_paraside", fake_generate)
    monkeypatch.setattr(
        nasal_air,
        "run_paraside",
        lambda command: subprocess.CompletedProcess(command, 0),
    )

    with pytest.raises(FileNotFoundError, match="Expected PARASIDE"):
        nasal_air.correct_fuzzy_nasal_air(
            4,
            output=tmp_path / "corrected.nii.gz",
            paraside_env=tmp_path / "env",
            paraside_model=tmp_path / "weights",
        )


def test_nasal_air_cli_reports_corrected_output(monkeypatch, tmp_path, capsys):
    """Test nasal-air CLI reports final corrected derivative output."""
    output = tmp_path / "corrected.nii.gz"
    seen = {}

    def fake_correct(*args, **kwargs):
        seen.update(kwargs)
        output.parent.mkdir(parents=True, exist_ok=True)
        save_array(np.zeros((1, 1, 1, 2), dtype=np.uint16), np.eye(4), output)
        sidecar = tmp_path / "corrected.json"
        sidecar.write_text("{}", encoding="utf-8")
        return nasal_air.NasalAirCorrectionResult(
            corrected_path=output,
            sidecar_path=sidecar,
            source_fuzzy_path=tmp_path / "cache" / "brainweb_s04_fuzzy.nii.gz",
            t1w_path=tmp_path / "t1w.nii.gz",
            paraside_mask_path=tmp_path / "mask.nii.gz",
            patched_voxels=1,
            metadata={},
        )

    monkeypatch.setattr(cli, "correct_fuzzy_nasal_air", fake_correct)
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-nasal-air-correct",
            "4",
            "--output",
            str(output),
            "--paraside-env",
            str(tmp_path / "env"),
            "--paraside-model",
            str(tmp_path / "weights"),
        ],
    )

    cli.nasal_air_main()

    captured = capsys.readouterr().out
    assert str(output) in captured
    assert "brainweb_s04_fuzzy.nii.gz" not in captured
    assert seen["paraside_env"] == tmp_path / "env"
    assert seen["t1w_snr"] == pytest.approx(10.0)
    assert "air_labels" not in seen


def test_nasal_air_cli_can_disable_t1w_noise_and_use_direct_executable(
    monkeypatch, tmp_path, capsys
):
    """Test nasal-air CLI maps --t1w-snr 0 to no T1w noise."""
    output = tmp_path / "corrected.nii.gz"
    seen = {}

    def fake_correct(*args, **kwargs):
        seen.update(kwargs)
        output.parent.mkdir(parents=True, exist_ok=True)
        save_array(np.zeros((1, 1, 1, 2), dtype=np.uint16), np.eye(4), output)
        sidecar = tmp_path / "corrected.json"
        sidecar.write_text("{}", encoding="utf-8")
        return nasal_air.NasalAirCorrectionResult(
            corrected_path=output,
            sidecar_path=sidecar,
            source_fuzzy_path=tmp_path / "cache" / "brainweb_s04_fuzzy.nii.gz",
            t1w_path=tmp_path / "t1w.nii.gz",
            paraside_mask_path=tmp_path / "mask.nii.gz",
            patched_voxels=1,
            metadata={},
        )

    monkeypatch.setattr(cli, "correct_fuzzy_nasal_air", fake_correct)
    monkeypatch.setattr(
        "sys.argv",
        [
            "brainweb-dl-nasal-air-correct",
            "4",
            "--output",
            str(output),
            "--paraside-executable",
            str(tmp_path / "paraside.exe"),
            "--paraside-model",
            str(tmp_path / "weights"),
            "--t1w-snr",
            "0",
            "--t1w-rng",
            "123",
        ],
    )

    cli.nasal_air_main()

    assert str(output) in capsys.readouterr().out
    assert seen["paraside_executable"] == tmp_path / "paraside.exe"
    assert seen["paraside_env"] is None
    assert seen["t1w_snr"] is None
    assert seen["t1w_rng"] == 123
    assert "air_labels" not in seen


def test_brainweb20_fuzzy_vessels_threshold_is_clamped(monkeypatch, tmp_path):
    """Test the BrainWeb20 vessels channel clamps the observed 16-value floor."""
    channels = (
        type("Channel", (), {"download_alias": "bck"})(),
        type("Channel", (), {"download_alias": "ves"})(),
    )
    table = type("Table", (), {"channels": channels})()
    seen = {}

    def fake_request(download_command, *args, **kwargs):
        if download_command.endswith("_ves"):
            return np.array([[[16, 17]]], dtype=np.uint16), np.eye(4)
        return np.array([[[5, 6]]], dtype=np.uint16), np.eye(4)

    def fake_save_array(data, affine, path):
        seen["data"] = data.copy()
        return path

    monkeypatch.setattr(brainweb, "BIG_RES_SHAPE", (1, 1, 2))
    monkeypatch.setattr(brainweb, "BIG_RES_TRANSPOSE", (0, 1, 2))
    monkeypatch.setattr(brainweb, "load_tissue_properties", lambda *args: table)
    monkeypatch.setattr(brainweb, "_request_get_brainweb", fake_request)
    monkeypatch.setattr(brainweb, "_request_get_brainweb_affine", lambda *args: np.eye(4))
    monkeypatch.setattr(brainweb, "save_array", fake_save_array)

    brainweb.get_brainweb20(4, brainweb_dir=tmp_path, segmentation="fuzzy", force=True)

    np.testing.assert_array_equal(seen["data"][..., 1], np.array([[[0, 17]]]))


@pytest.mark.parametrize("seg", ["fuzzy", "crisp"])
def test_get_seg(seg, bw_dir, force):
    """Test retrieval of available data."""
    paths = get_brainweb20_multiple(
        [4, 44], segmentation=seg, brainweb_dir=bw_dir, force=force
    )
    print(paths)


@pytest.mark.parametrize("seg", ["fuzzy", "crisp"])
def test_get_seg2(seg, bw_dir, force):
    """Test retrieval of available data."""
    paths = get_brainweb1_seg(segmentation=seg, brainweb_dir=bw_dir, force=force)
    print(paths)
