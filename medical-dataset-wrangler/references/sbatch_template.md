# sbatch template for dataset downloads

Use this template when generating an sbatch script for a download job.
Fill in the `<PLACEHOLDERS>` from the user's request.

## Template

```bash
#!/bin/bash
#SBATCH --account=<ACCOUNT>
#SBATCH --job-name=<JOB_NAME>
#SBATCH --time=<WALL_TIME>
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

set -euo pipefail

# Load modules (adjust if the user has different conventions)
module load python/3.11 StdEnv/2023

# Activate venv with the needed CLI tools installed
source <VENV_PATH>/bin/activate

# Destination
DEST=<DEST_PATH>
mkdir -p "$DEST"

# <DOWNLOAD COMMAND HERE>
# e.g. gdc-client download -m /path/to/manifest.txt -d "$DEST"
# e.g. kaggle competitions download -c <slug> -p "$DEST"
# e.g. python /path/to/hf_download.py --repo-id ... --revision ... --local-dir "$DEST"

# Post-download sanity check
FILE_COUNT=$(find "$DEST" -type f | wc -l)
echo "Downloaded $FILE_COUNT files to $DEST"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "ERROR: no files downloaded" >&2
    exit 1
fi
```

## Placeholder guidance

- **ACCOUNT**: for our lab, typically `def-jma-ab`. Only use this if the user
  confirms the account or it's already in their memory context.
- **WALL_TIME**: rough estimate based on source:
  - TCGA cohort, ~100 GB: `12:00:00`
  - TCGA cohort, <20 GB: `4:00:00`
  - Kaggle competition: `2:00:00`
  - HF dataset: depends on size, usually `4:00:00` is safe
- **JOB_NAME**: something short and identifiable, e.g. `cesc-download`
- **DEST_PATH**: if the user mentions `$SCRATCH` or `$SLURM_TMPDIR`, use that.
  Prefer `$SCRATCH` for datasets that need to persist past the job.
- **VENV_PATH**: ask the user if it's not obvious from context.

## Notes

- Don't request a GPU for downloads. Waste of allocation.
- Don't run `gdc-client` inside `$SLURM_TMPDIR` — it's wiped when the job ends.
  Use `$SCRATCH` for downloads that need to persist.
- For very large downloads (>500 GB), consider breaking the manifest into
  chunks and submitting as an array job, but that's beyond this template.
