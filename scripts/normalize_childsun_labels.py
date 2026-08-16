"""Normalize ChildSUn YOLO labels to object-detection bounding boxes.

The source dataset mixes YOLO detection rows (class xc yc w h) and
segmentation polygons (class x1 y1 x2 y2 ...).  This script backs up the
original labels, then converts every polygon to its enclosing normalized box.
"""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path


SPLITS = ("train", "val", "test")


def normalize_row(parts: list[str], label_path: Path, line_number: int) -> tuple[str, bool]:
    """Return a normalized YOLO box row and whether the input was a polygon."""
    try:
        values = [float(value) for value in parts]
    except ValueError as error:
        raise ValueError(f"{label_path}:{line_number}: non-numeric label") from error

    if len(values) == 5:
        class_id, x_center, y_center, width, height = values
        is_polygon = False
    elif len(values) >= 7 and len(values) % 2 == 1:
        class_id = values[0]
        coordinates = values[1:]
        xs, ys = coordinates[::2], coordinates[1::2]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_center, y_center = (x_min + x_max) / 2, (y_min + y_max) / 2
        width, height = x_max - x_min, y_max - y_min
        is_polygon = True
    else:
        raise ValueError(
            f"{label_path}:{line_number}: expected 5 detection values or an even number of polygon coordinates"
        )

    if class_id != int(class_id) or not 0 <= class_id < 5:
        raise ValueError(f"{label_path}:{line_number}: invalid class id {class_id}")
    if not all(0.0 <= value <= 1.0 for value in (x_center, y_center, width, height)):
        raise ValueError(f"{label_path}:{line_number}: coordinates outside [0, 1]")
    if x_center - width / 2 < 0 or x_center + width / 2 > 1:
        raise ValueError(f"{label_path}:{line_number}: box exceeds horizontal image boundary")
    if y_center - height / 2 < 0 or y_center + height / 2 > 1:
        raise ValueError(f"{label_path}:{line_number}: box exceeds vertical image boundary")

    return f"{int(class_id)} {x_center:.8f} {y_center:.8f} {width:.8f} {height:.8f}", is_polygon


def collect_normalized_labels(dataset_dir: Path) -> tuple[dict[Path, str], Counter]:
    """Validate all labels before changing any source file."""
    converted: dict[Path, str] = {}
    stats: Counter = Counter()

    for split in SPLITS:
        labels_dir = dataset_dir / split / "labels"
        if not labels_dir.is_dir():
            raise FileNotFoundError(f"Missing labels directory: {labels_dir}")
        for label_path in sorted(labels_dir.glob("*.txt")):
            rows: list[str] = []
            for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                normalized, is_polygon = normalize_row(line.split(), label_path, line_number)
                rows.append(normalized)
                stats["polygon_rows" if is_polygon else "detection_rows"] += 1
            converted[label_path] = "\n".join(rows) + ("\n" if rows else "")
            stats[f"{split}_files"] += 1
            stats["label_files"] += 1

    return converted, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert mixed ChildSUn labels to YOLO detection boxes")
    parser.add_argument("--dataset-dir", type=Path, default=Path("data/childsun"))
    parser.add_argument("--backup-dir", type=Path, default=Path("data/childsun_original_labels"))
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    backup_dir = args.backup_dir.resolve()
    if backup_dir.exists():
        raise FileExistsError(f"Backup directory already exists: {backup_dir}")

    converted, stats = collect_normalized_labels(dataset_dir)

    # Preserve only the original label trees; images are not copied.
    backup_dir.mkdir(parents=True)
    for split in SPLITS:
        shutil.copytree(dataset_dir / split / "labels", backup_dir / split / "labels")

    for label_path, content in converted.items():
        label_path.write_text(content, encoding="utf-8", newline="\n")

    print(f"Backup: {backup_dir}")
    print(f"Label files: {stats['label_files']}")
    print(f"Detection rows preserved: {stats['detection_rows']}")
    print(f"Polygon rows converted: {stats['polygon_rows']}")


if __name__ == "__main__":
    main()
