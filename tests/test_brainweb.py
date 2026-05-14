"""Test for the brainweb module."""

import numpy as np
from nibabel import nifti1 as nifti

import pytest
from brainweb_dl import (
    get_mri,
    get_brainweb20_multiple,
    get_brainweb1_seg,
    get_quantitative_map,
    load_tissue_properties,
    save_quantitative_map,
)
import brainweb_dl.cli as cli
import brainweb_dl.mri as mri
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
