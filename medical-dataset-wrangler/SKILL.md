---
name: medical-dataset-wrangler
description: Download medical imaging datasets and convert them into standard training-ready formats. Use this skill whenever the user wants to pull data from TCGA/GDC, Kaggle, HuggingFace, or Google Drive, convert DICOM series to NIfTI, or format a dataset for nnUNetv2 — even if they phrase it casually ("grab the CESC slides", "make this nnUNet-ready", "convert these scans"). Also trigger when the user mentions writing an sbatch script for a dataset download, building a `dataset.json`, creating patient-level train/val/test splits, or staging data into `$SCRATCH` / `$SLURM_TMPDIR`.
---

# Medical Dataset Wrangler

A skill for downloading medical imaging datasets and doing the two preprocessing steps that are generic enough to automate: DICOM → NIfTI conversion and nnUNetv2 formatting.

The skill does *not* try to be a universal downloader — it generates the right commands and sbatch scripts, but the user still kicks off long-running downloads themselves.

## Scope

**This skill handles:**
- Generating GDC manifests + sbatch scripts for TCGA cohorts
- Kaggle competition and dataset pulls
- HuggingFace `snapshot_download` with revision pinning
- `gdown` for shared Google Drive folders
- DICOM series → NIfTI conversion (orientation, spacing, modality preserved)
- nnUNetv2 dataset formatting (`imagesTr/`, `labelsTr/`, `dataset.json`, splits)
- Provenance manifests for every dataset produced

**This skill does NOT handle:**
- WSI tiling, stain normalization, or tissue detection (dataset-specific, needs its own skill)
- Controlled-access TCGA data (user must manage their own GDC token)
- Private/gated HF datasets beyond running `huggingface-cli login`

If the user asks for WSI preprocessing, tell them this skill doesn't cover it and suggest they build a separate one.

## Workflow

1. **Identify the task.** Is the user asking to (a) download something, (b) convert DICOM, (c) format for nnUNet, or (d) some combination? Most requests are (a) then (c), or just (b)→(c).

2. **Check prerequisites** before running anything. For each source the user wants:
   - **GDC**: `gdc-client` installed? Token file if they need controlled access?
   - **Kaggle**: `~/.kaggle/kaggle.json` present? For competitions, have they accepted the rules on the website? (The CLI will silently fail otherwise.)
   - **HuggingFace**: `huggingface-cli login` done if the dataset is gated?
   - **gdown**: link is a shared folder/file, not a private one?

   If prerequisites are missing, tell the user what to do and stop — don't try to work around auth.

3. **Run or generate.** For small pulls, run them directly. For anything that will take more than a few minutes or is >5 GB, generate an sbatch script and tell the user to submit it. See `references/sbatch_template.md` for the template.

4. **Preprocess.** Use the scripts in `scripts/` rather than rewriting the conversion logic. They handle the edge cases (mixed orientations, non-contiguous labels, empty series, etc.) that tend to bite people.

5. **Write a manifest.** Every dataset produced by this skill gets a `_manifest.json` recording the source, download date, git-style checksum of the file list, and any parameters used. This is non-negotiable — it's how we reproduce things later.

## Download recipes

See `references/downloads.md` for the full details of each source. Quick summary:

| Source | Command | Notes |
|---|---|---|
| TCGA (open) | `scripts/gdc_manifest.py` → `gdc-client download -m manifest.txt` | Filter by project, sample type, data format via GDC API |
| Kaggle | `kaggle competitions download` or `kaggle datasets download` | Requires accepted rules for competitions |
| HuggingFace | `scripts/hf_download.py` | Pins to a specific revision (commit SHA) |
| Google Drive | `gdown <url>` or `gdown --folder <url>` | Public/shared only; no reliable resume |

## DICOM → NIfTI

Use `scripts/dicom_to_nifti.py`. It wraps SimpleITK's series reader and preserves orientation, spacing, and origin. It will not silently collapse multi-series folders — if it finds more than one series, it errors and lists them so the user can pick.

```
python scripts/dicom_to_nifti.py <input_dir> <output.nii.gz>
```

For multi-modality cases (e.g., PET + CT), run it once per modality and name the outputs with the nnUNet convention: `<case>_0000.nii.gz`, `<case>_0001.nii.gz`, etc.

## nnUNetv2 formatting

Use `scripts/make_nnunet_dataset.py`. Given a directory of per-case NIfTI images + masks, it:
- Builds the `Dataset###_Name/` folder with `imagesTr/` and `labelsTr/`
- Generates a valid `dataset.json` with the channels the user specifies
- Checks labels are contiguous starting from 0 (background) and reports if not
- Creates patient-level splits with a fixed seed (default 42)

```
python scripts/make_nnunet_dataset.py \
  --raw-dir <path> \
  --dataset-id 234 \
  --dataset-name PETCT \
  --channels CT PET \
  --labels "background,lesion" \
  --output-root $nnUNet_raw
```

See `references/nnunet_format.md` for the exact layout and the `dataset.json` schema.

## Provenance manifest

Every dataset the skill produces must include a `_manifest.json` at its root:

```json
{
  "dataset_name": "Dataset234_PETCT",
  "created": "2026-04-24T14:00:00Z",
  "source": {
    "type": "local_dicom",
    "input_path": "/home/user/raw_pet"
  },
  "preprocessing": {
    "dicom_to_nifti": "SimpleITK 2.3.1",
    "channels": ["CT", "PET"],
    "labels": {"0": "background", "1": "lesion"}
  },
  "num_cases": 42,
  "split_seed": 42,
  "file_checksum": "sha256:..."
}
```

The `scripts/write_manifest.py` helper generates this from the dataset directory.

## Examples

**Example 1: Pull CESC slides and stage them**

User: "Generate a GDC manifest and sbatch to pull CESC FFPE diagnostic slides to $SCRATCH/datasets/CESC_wsi"

Steps:
1. Run `scripts/gdc_manifest.py --project TCGA-CESC --sample-type "Primary Tumor" --data-format SVS --preservation FFPE -o cesc_manifest.txt`
2. Generate an sbatch script using `references/sbatch_template.md`, filling in the manifest path and output dir
3. Show the user both files and tell them to `sbatch` it

**Example 2: Convert DICOM to NIfTI and format for nnUNet**

User: "Convert DICOM in ~/raw_pet to NIfTI as Dataset234_PETCT for nnUNetv2, CT=0 PET=1"

Steps:
1. Inspect `~/raw_pet` — figure out the per-case structure (one folder per patient? per study?)
2. Loop over cases: run `dicom_to_nifti.py` once per modality, naming outputs `<case>_0000.nii.gz` (CT) and `<case>_0001.nii.gz` (PET)
3. If masks exist, copy them to a parallel `labels/` dir as `<case>.nii.gz`
4. Run `make_nnunet_dataset.py` with `--channels CT PET` and the user's label spec
5. Write the manifest

**Example 3: Kaggle competition pull**

User: "Pull the RSNA pneumonia competition from Kaggle to $SCRATCH/datasets/rsna_pneumonia"

Steps:
1. Check `~/.kaggle/kaggle.json` exists
2. Remind the user to accept the rules on kaggle.com if they haven't
3. Run `kaggle competitions download -c rsna-pneumonia-detection-challenge -p $SCRATCH/datasets/rsna_pneumonia`
4. Unzip, write manifest

## Principles

- **Fail loudly, not silently.** If a DICOM series is missing slices, if labels aren't contiguous, if a manifest download returns zero files — stop and tell the user. Don't paper over it.
- **The user controls long-running work.** Generate sbatch scripts for anything slow; don't block a Claude turn on a 4-hour download.
- **Every dataset gets a manifest.** No exceptions.
- **Prefer the scripts over inline code.** They've been debugged already; reinventing them per-session invites regressions.
