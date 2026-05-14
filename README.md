# Brainweb-DL

Welcome to Brainweb-DL, a powerful Python toolkit for downloading and converting the Brainweb dataset. 

<p align="center">
<a href=https://github.com/paquiteau/brainweb-dl/blob/master/LICENSE><img src=https://img.shields.io/github/license/paquiteau/brainweb-dl></a>
<a href=https://www.codefactor.io/repository/github/paquiteau/brainweb-dl><img src=https://www.codefactor.io/repository/github/paquiteau/brainweb-dl/badge></a>
<a href=https://github.com/psf/black><img src=https://img.shields.io/badge/style-black-black></a>
<a href=https://pypi.org/project/brainweb-dl><img src=https://img.shields.io/pypi/v/brainweb-dl></a>
<a href=https://pypi.org/project/brainweb-dl><img src=https://img.shields.io/pypi/pyversions/brainweb-dl></a>
</p>

## Features

- **Effortless Dataset Management:** Automatically download, cache, and format the Brainweb dataset with ease. Convert it to the convenient nifti format or numpy array hassle-free.

- **Quantitative Map Generation:** Generate apparent T1, T2, T2*, ADC, susceptibility, proton-density, and volume-fraction maps from BrainWeb20 fuzzy segmentations using structured tissue-property metadata.

- **Analytical Contrast Synthesis:** Synthesize simple T1w, T2w, and T2*w magnitude images from quantitative maps using spin-echo, SPGR/FLASH, or GRE equations with optional white-matter-calibrated Rician noise.

### Available data 

The Brainweb project kindly provides:
 
 - A normal brain phantom (named subject `0` afterwards), with T1, T2 and PD contrasts, with a variety of noise levels and intensity non-uniformities. As well as a anatomical model (in the form of either crisp or fuzzy segmentation of brain tissues, at a fixed resolution of 181x217x181 images).
 - The same for a multiple sclerosis brain phantom (named subject `1` afterwards). 
 - A set of 20 normal brains (with ids equal to `[4, 5, 6, 18, 20, 38, 41-54]`) , with a T1 contrast (with 1mm resolution at (181, 217,181)), as well as the crisp and fuzzy segmentation of brain tissues (with a shape of (362, 434,362)) [^1].
 
This project provides a **CLI** and a **Python API** to download and convert theses data. On top of that, it can generate quantitative maps from BrainWeb20 fuzzy segmentations, and reshape the data to the desired resolution [^2].


[^1]: Note that the classification of tissue is not the same as for subject 0 and 1
[^2]: This requires scipy to be installed. 

## Get Started

### Data Location

The BrainWeb cache/download directory follows this priority order:

1. User-specific argument (`brainweb_dir` in most functions)
2. `BRAINWEB_DIR` environment variable
3. `~/.cache/brainweb` folder

### Python Script Usage
```python
from brainweb_dl import get_mri 

# Get the phantom with id 44 with a T1 constrast 
data = get_mri(sub_id=44, contrast="T1") 
# Gt the 3rd phantomn with a fuzzy segmentation of its tissues. 
data = get_mri(sub_id="3", contrast="fuzzy") 

# Check the docstring for more information.
```

The Brainweb dataset is downloaded and cached by default in the `~/.cache/brainweb` folder.

### Quantitative Maps

BrainWeb20 quantitative maps are generated from a fuzzy segmentation in a separate step:

```python
from brainweb_dl import get_mri, get_quantitative_map

fuzzy, affine = get_mri(sub_id=44, contrast="fuzzy", with_affine=True)
t2 = get_quantitative_map(fuzzy, "T2", affine=affine, field_strength=3.0)
```

The fuzzy channels are converted to tissue volume fractions by dividing each channel by `4095`; channels are not renormalized per voxel. Relaxation maps are returned in seconds using proton-density-weighted apparent rate estimates. Proton density is represented in `[0, 1]`, and susceptibility is represented in ppm. Generated maps are apparent parameter maps, not full MRI sequence simulations.

### Analytical Contrast Synthesis

Quantitative maps can be turned into simple weighted magnitude images with the
analytical contrast API:

```python
from brainweb_dl import ContrastMaps, ContrastSequence, synthesize_contrast

result = synthesize_contrast(
    ContrastMaps(PD=pd_map, T1=t1_map, T2s=t2s_map, affine=affine),
    ContrastSequence(model="flash", TR=0.025, TE=0.004, flip_angle=20),
    contrast="T1w",
)
```

The same API accepts map paths, which is useful after saving qmap outputs:

```python
from brainweb_dl import ContrastMaps, ContrastSequence, synthesize_contrast

result = synthesize_contrast(
    ContrastMaps(PD="pd.nii.gz", T1="t1.nii.gz", T2s="t2s.nii.gz"),
    ContrastSequence(model="spgr", TR=0.025, TE=0.004, flip_angle=20),
)
```

Signal conventions are deliberately small in scope:

- Spin echo: `PD * (1 - exp(-TR / T1)) * exp(-TE / T2)`
- SPGR/FLASH: `PD * sin(alpha) * (1 - E1) / (1 - cos(alpha) * E1)`, with optional `exp(-TE / T2s)` decay
- GRE T2*w: `PD * exp(-TE / T2s)`

`TR` and `TE` are in seconds, flip angle is in degrees, and relaxation maps are
expected in seconds. The synthesizer only requires maps used by the selected
model. Optional noisy magnitude output uses Rician statistics calibrated from
the mean clean signal in BrainWeb fuzzy white-matter voxels:
`sigma = mean(clean_signal[white_matter_mask]) / snr`. This is not a Bloch,
k-space, coil, B0/B1, or reconstruction simulator.

### Command Line Interface

```bash
brainweb-dl 44 --contrast=T1 --output-dir ./brainweb-output
```

Quantitative maps use the dedicated CLI:

```bash
brainweb-dl-qmap 44 --property T2 --field-strength 3 --output brainweb_s44_T2.nii.gz
brainweb-dl-qmap 44 --property all --output brainweb_s44_qmaps.h5
```

Analytical synthesis can consume saved qmap paths:

```bash
brainweb-dl-synth --model flash --pd pd.nii.gz --t1 t1.nii.gz --t2s t2s.nii.gz --tr 0.025 --te 0.004 --flip-angle 20 --output t1w_flash.nii.gz
brainweb-dl-synth --model gre --contrast T2*w --pd pd.nii.gz --t2s t2s.nii.gz --te 0.03 --snr 40 --fuzzy brainweb_s44_fuzzy.nii.gz --output t2sw_noisy.nii.gz
```

`--brainweb-dir` controls where native BrainWeb files are cached or reused.
`--output-dir` controls where the final requested CLI output is saved. When
`--output-dir` is omitted, the final output is saved in the current working
directory.

For compatibility with older versions, note that segmentation commands no
longer treat `--brainweb-dir` as the final output location when `--output-dir`
is provided. Use `--output-dir` for the directory that should contain the
requested `T1`, `T2`, `T2*`, `crisp`, or `fuzzy` output file.

For more information, see `brainweb-dl --help`.

## Installation 

Get up and running quickly!

```bash 
pip install brainweb-dl
```

### Development

Join our community and contribute to Brainweb-DL!

```bash
git clone git@github.com/paquiteau/brainweb-dl 
cd brainweb-dl
pip install -e .[dev,test,doc]
```

### TODO List
Help us improve and shape the future of Brainweb-DL:

- [x] Add unit tests.
- [x] Implement fuzzy search and multiple subjects download in parallel.
- [x] Develop an interface to generate quantitative maps from BrainWeb segmentations.
- [x] Enhance the search for the location of the Brainweb dataset (User > Environment Variable > Default Location).
- [ ] Introduce an interface to download as BIDS format.

## Acknowledgement

We extend our gratitude to the following for their contributions:

- [Casper De Clercq](https://github.com/casperdcl/brainweb/) for the preliminary work and original idea. Check out his great work if you are interested in PET imaging and registration functionalities.

- [BrainWeb](https://brainweb.bic.mni.mcgill.ca/) for providing this valuable dataset to the community.



<p align=center> :star2: If you like this work, don't forget to star it and share it 🌟 </p>
