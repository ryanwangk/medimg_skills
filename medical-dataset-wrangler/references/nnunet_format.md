# nnUNetv2 dataset format

Reference for the layout and `dataset.json` schema that `make_nnunet_dataset.py`
produces. Read this when you need to debug a formatting issue or the user
wants something non-standard.

## Directory layout

```
$nnUNet_raw/
    Dataset<ID>_<Name>/
        imagesTr/
            case001_0000.nii.gz       # modality 0 (e.g. CT)
            case001_0001.nii.gz       # modality 1 (e.g. PET)
            case002_0000.nii.gz
            case002_0001.nii.gz
            ...
        labelsTr/
            case001.nii.gz            # no modality suffix on labels
            case002.nii.gz
            ...
        imagesTs/                     # optional, same convention as imagesTr
        dataset.json
        splits_final.json             # our addition, seeded patient-level CV
```

- `<ID>` is a 3-digit zero-padded integer (e.g. `234`).
- `<Name>` is short, alphanumeric+underscore, descriptive (e.g. `PETCT`, `LiverSeg`).
- Image files: `<case_id>_<channel>.nii.gz` where channel is 4-digit zero-padded.
- Label files: `<case_id>.nii.gz` with integer voxel values.

## dataset.json schema

Minimum required fields for nnUNetv2:

```json
{
  "channel_names": {
    "0": "CT",
    "1": "PET"
  },
  "labels": {
    "background": 0,
    "lesion": 1
  },
  "numTraining": 42,
  "file_ending": ".nii.gz"
}
```

**Channel names** affect nnUNet's normalization defaults — use canonical
names like `CT`, `MRI`, `PET`, `noNorm` where appropriate.

**Labels** must start at 0 (background) and be contiguous integers.
If the source masks have gaps (e.g. labels `{0, 1, 3}`), remap them before
this step.

## Regions-based labels (advanced)

For tasks like BraTS where you want to train on overlapping regions
(whole tumor, tumor core, enhancing tumor), use the nested format:

```json
{
  "labels": {
    "background": 0,
    "whole_tumor": [1, 2, 3],
    "tumor_core": [2, 3],
    "enhancing_tumor": [3]
  },
  "regions_class_order": [1, 2, 3]
}
```

The script doesn't generate this by default — handle it manually if the
user asks.

## Splits

nnUNet will auto-generate 5-fold splits if `splits_final.json` is absent,
but we generate our own to guarantee patient-level splits with a fixed
seed. The format is:

```json
[
  {"train": ["case001", "case003", ...], "val": ["case002", "case005", ...]},
  {"train": [...], "val": [...]},
  ...
]
```

Note: case ids here are bare (no channel suffix, no extension).

## Common failures

- **Non-contiguous labels**: `make_nnunet_dataset.py` doesn't currently
  remap — if the source has `{0, 1, 3}`, the resulting dataset will fail
  planning. Fix by remapping the masks before calling the script.
- **Missing modality for a case**: the script skips these and prints a warning.
  Check stderr.
- **Mismatched image/label sizes**: nnUNet's planner catches these, not us.
  If the user reports a planner error, suggest `nnUNetv2_plan_and_preprocess
  -d <ID> --verify_dataset_integrity` and inspect the output.
