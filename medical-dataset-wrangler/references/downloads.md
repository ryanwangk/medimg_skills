# Download recipes

Details for each data source this skill supports. Read the section relevant
to the user's request — you don't need to read all of them every time.

## Table of contents
- TCGA via GDC
- Kaggle
- HuggingFace
- Google Drive
- When to generate an sbatch script

---

## TCGA via GDC

Use `scripts/gdc_manifest.py` to generate a manifest, then `gdc-client`
to download.

**Common filters:**
- `--project` — e.g. `TCGA-CESC`, `TCGA-PAAD`, `TCGA-TGCT`, `TCGA-PCPG`, `TCGA-UCS`
- `--sample-type` — `"Primary Tumor"`, `"Solid Tissue Normal"`, `"Recurrent Tumor"`
- `--data-format` — `SVS` (WSI), `BAM`, `VCF`, `TXT`, `TSV`
- `--data-category` — `"Slide Image"`, `"Transcriptome Profiling"`, etc.
- `--preservation` — `FFPE` or `Frozen`

**Open vs. controlled:** diagnostic WSIs and many derived files are open.
BAMs and raw sequencing are controlled and require a dbGaP-approved token
(`GDC_TOKEN_FILE`). This skill defaults to `--access open`. For controlled
data, the user manages their own token — don't try to set it up for them.

**Typical cohort sizes to set expectations:**
- TCGA-CESC diagnostic slides FFPE: ~270 files, ~100 GB
- TCGA-PAAD diagnostic slides FFPE: ~195 files, ~80 GB
- TCGA-UCS diagnostic slides FFPE: ~57 files, ~20 GB

Anything over ~5 GB should go through sbatch, not a live Claude turn.

**Download command after manifest:**
```bash
gdc-client download -m manifest.txt -d $SCRATCH/datasets/<cohort>
```

Each file lands in its own subdirectory named by UUID. If the user wants a
flat layout, they'll need to post-process — don't do that automatically,
since the UUID structure is what links back to GDC metadata.

---

## Kaggle

**Prerequisite check:** verify `~/.kaggle/kaggle.json` exists and is chmod 600.
If not, stop and tell the user to set it up from kaggle.com → Account → API.

**For competitions:** the user must have clicked "I accept the rules" on
the competition page. Without that, `kaggle competitions download` returns
a 403 silently. Always mention this before running.

**Commands:**
```bash
# Competition
kaggle competitions download -c <competition-slug> -p <dest>

# Dataset (user/name format)
kaggle datasets download -d <owner>/<dataset-name> -p <dest> --unzip
```

The `--unzip` flag only works for datasets, not competitions. For
competitions, unzip manually.

---

## HuggingFace

Use `scripts/hf_download.py` — it wraps `snapshot_download` and enforces
revision pinning.

**Why pin the revision:** HuggingFace repos are mutable. `main` can change
under you. Pinning to a commit SHA gives you a truly reproducible dataset.
If the user doesn't provide a revision, the script resolves the current HEAD
and prints it so they can pin it next time.

**Gated datasets:** many medical datasets (MIMIC derivatives, some
radiology collections) are gated. The user must:
1. Accept the terms on the dataset's HF page
2. Run `huggingface-cli login` with a token that has read access

If those aren't done, `snapshot_download` raises an HTTP 401/403. Relay
the error to the user rather than trying to work around it.

**Narrowing downloads:** for large repos, use `--allow-patterns` to pull
only what's needed. E.g. `--allow-patterns "*.nii.gz" "metadata.csv"`.

---

## Google Drive

Use `gdown`. It works for:
- Public files: `gdown <file-url-or-id>`
- Public/shared folders: `gdown --folder <folder-url>`

**Known limits:**
- No reliable resume. If a large download dies, you usually re-pull from scratch.
- Google rate-limits popular files — the error is "Too many users have viewed
  or downloaded this file recently." The workaround is waiting 24 hours or
  asking the file owner for a different share link. This skill cannot fix it.
- Private/restricted folders need the Drive API with OAuth, which is out of scope.

For anything over a few GB, prefer a different source if one exists.

---

## When to generate an sbatch script

Use sbatch if any of these apply:
- Total download >5 GB
- Expected wall time >30 minutes
- The user mentions `$SCRATCH`, `$SLURM_TMPDIR`, `def-jma-ab`, or a cluster
- The user asks for it explicitly

See `references/sbatch_template.md` for the template.
