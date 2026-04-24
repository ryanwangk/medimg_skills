#!/usr/bin/env python3
"""Convert a DICOM series to a single NIfTI file using SimpleITK.

Preserves orientation, spacing, and origin. Refuses to run if the input
directory contains more than one DICOM series — instead lists them so
the caller can pick.

Example:
    python dicom_to_nifti.py /path/to/dicom_dir output.nii.gz
"""
import argparse
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input_dir", help="Directory containing DICOM files")
    p.add_argument("output", help="Output NIfTI path (should end in .nii.gz)")
    p.add_argument("--series-uid", help="If the dir has multiple series, pick this one")
    args = p.parse_args()

    try:
        import SimpleITK as sitk
    except ImportError:
        print("ERROR: SimpleITK not installed. Run: pip install SimpleITK", file=sys.stderr)
        sys.exit(1)

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"ERROR: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(input_dir))

    if not series_ids:
        print(f"ERROR: no DICOM series found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    if len(series_ids) > 1 and not args.series_uid:
        print(f"ERROR: found {len(series_ids)} series in {input_dir}. Pick one with --series-uid:", file=sys.stderr)
        for sid in series_ids:
            files = reader.GetGDCMSeriesFileNames(str(input_dir), sid)
            print(f"  {sid}  ({len(files)} slices)", file=sys.stderr)
        sys.exit(1)

    series_uid = args.series_uid or series_ids[0]
    files = reader.GetGDCMSeriesFileNames(str(input_dir), series_uid)
    reader.SetFileNames(files)
    image = reader.Execute()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(out_path))

    size = image.GetSize()
    spacing = image.GetSpacing()
    print(f"Wrote {out_path}")
    print(f"  size: {size}")
    print(f"  spacing: {tuple(round(s, 4) for s in spacing)}")
    print(f"  slices read: {len(files)}")


if __name__ == "__main__":
    main()
