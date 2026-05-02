"""
Script tải dataset ChildSUn và Violence.

Usage:
    python scripts/download_dataset.py --dataset childsun
    python scripts/download_dataset.py --dataset violence
    python scripts/download_dataset.py --all
"""

import argparse
from pathlib import Path

from loguru import logger


def create_dataset_structure(base_dir: Path, name: str) -> None:
    """Tạo cấu trúc thư mục dataset."""
    for split in ["train", "val", "test"]:
        (base_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (base_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    logger.info(f"Created dataset structure at: {base_dir}")
    logger.info(
        f"Please place your {name} dataset files in the appropriate directories:\n"
        f"  - Images: {base_dir}/{{train,val,test}}/images/\n"
        f"  - Labels: {base_dir}/{{train,val,test}}/labels/"
    )


def main():
    parser = argparse.ArgumentParser(description="Download/prepare datasets")
    parser.add_argument("--dataset", choices=["childsun", "violence"], help="Dataset to prepare")
    parser.add_argument("--all", action="store_true", help="Prepare all datasets")
    parser.add_argument("--output", default="./data", help="Output directory")
    args = parser.parse_args()

    output = Path(args.output)

    if args.all or args.dataset == "childsun":
        create_dataset_structure(output / "childsun", "ChildSUn")

    if args.all or args.dataset == "violence":
        create_dataset_structure(output / "violence", "Violence")
        # Tạo thêm thư mục skeleton
        for split in ["train", "val", "test"]:
            (output / "violence" / split / "skeletons").mkdir(parents=True, exist_ok=True)
            (output / "violence" / split / "videos").mkdir(parents=True, exist_ok=True)

    if not args.all and not args.dataset:
        parser.print_help()


if __name__ == "__main__":
    main()
